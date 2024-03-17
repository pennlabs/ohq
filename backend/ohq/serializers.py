import string

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.crypto import get_random_string
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from rest_live.signals import save_handler
from schedule.models import Calendar, Event, EventRelation, EventRelationManager, Rule
from schedule.models.events import Occurrence

from ohq.models import (
    Announcement,
    Course,
    CourseStatistic,
    Document,
    Membership,
    MembershipInvite,
    Profile,
    Question,
    Queue,
    QueueStatistic,
    Semester,
    Tag,
    VectorDB,
)
from ohq.sms import sendSMSVerification
from ohq.tasks import sendUpNextNotificationTask


class CourseRouteMixin(serializers.ModelSerializer):
    """
    Mixin for serializers that overrides the save method to
    properly handle the URL parameter for courses.
    """

    def save(self):
        self.validated_data["course"] = Course.objects.get(
            pk=self.context["view"].kwargs["course_pk"]
        )
        return super().save()


class QueueRouteMixin(serializers.ModelSerializer):
    """
    Mixin for serializers that overrides the save method to
    properly handle the URL parameter for queues.
    """

    def save(self):
        self.validated_data["queue"] = Queue.objects.get(pk=self.context["view"].kwargs["queue_pk"])
        return super().save()


class SemesterSerializer(serializers.ModelSerializer):
    pretty = serializers.SerializerMethodField()

    class Meta:
        model = Semester
        fields = ("id", "year", "term", "pretty")

    def get_pretty(self, obj):
        return str(obj)


class CourseSerializer(serializers.ModelSerializer):
    semester_pretty = serializers.StringRelatedField(source="semester")
    is_member = serializers.BooleanField(default=False, read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "course_code",
            "department",
            "course_title",
            "description",
            "semester",
            "semester_pretty",
            "archived",
            "invite_only",
            "is_member",
        )


class CourseCreateSerializer(serializers.ModelSerializer):
    created_role = serializers.CharField(write_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "course_code",
            "department",
            "course_title",
            "description",
            "semester",
            "archived",
            "invite_only",
            "created_role",
        )

    def create(self, validated_data):
        kind = validated_data.pop("created_role")
        instance = super().create(validated_data)
        Membership.objects.create(course=instance, user=self.context["request"].user, kind=kind)
        return instance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email", "username")


class MembershipSerializer(CourseRouteMixin):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "kind", "time_created", "last_active", "user")

    def create(self, validated_data):
        ModelClass = self.Meta.model
        validated_data["user"] = self.context["request"].user
        validated_data["kind"] = Membership.KIND_STUDENT
        return ModelClass._default_manager.create(**validated_data)


class MembershipInviteSerializer(CourseRouteMixin):
    class Meta:
        model = MembershipInvite
        fields = ("id", "email", "kind", "time_created")

    def validate_email(self, value):
        return value.lower()


class QueueSerializer(CourseRouteMixin):
    questions_active = serializers.IntegerField(default=0, read_only=True)
    questions_asked = serializers.IntegerField(default=0, read_only=True)
    staff_active = serializers.IntegerField(default=0, read_only=True)

    class Meta:
        model = Queue
        fields = (
            "id",
            "name",
            "description",
            "question_template",
            "archived",
            "estimated_wait_time",
            "active",
            "questions_active",
            "questions_asked",
            "staff_active",
            "rate_limit_enabled",
            "rate_limit_length",
            "rate_limit_questions",
            "rate_limit_minutes",
            "video_chat_setting",
            "pin",
            "pin_enabled",
        )
        read_only_fields = ("estimated_wait_time",)

    def update(self, instance, validated_data):
        """
        Head TAs+ can modify a queue
        TAs can only modify if a queue is active.
        """

        user = self.context["request"].user
        membership = Membership.objects.get(course=instance.course, user=user)

        # generate a random pin when the queue is opened and the queue has pin enabled
        if "active" in validated_data and validated_data["active"] and instance.pin_enabled:
            validated_data["pin"] = get_random_string(
                length=5, allowed_chars=string.ascii_letters + string.digits
            )

        if membership.is_leadership:  # User is a Head TA+
            return super().update(instance, validated_data)

        if "active" in validated_data:
            instance.active = validated_data["active"]

        if "pin" in validated_data:
            instance.pin = validated_data["pin"]

        instance.save()
        return instance

    def to_representation(self, instance):
        # get the original representation
        rep = super(QueueSerializer, self).to_representation(instance)

        user = self.context["request"].user
        membership = Membership.objects.filter(course=instance.course, user=user).first()

        if membership is None or not membership.is_ta:
            rep.pop("pin")

        return rep


class TagSerializer(CourseRouteMixin):
    class Meta:
        model = Tag
        fields = ("id", "name")


class QuestionSerializer(QueueRouteMixin):
    asked_by = UserSerializer(read_only=True)
    responded_to_by = UserSerializer(read_only=True)
    tags = TagSerializer(many=True)
    position = serializers.IntegerField(default=-1, read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "text",
            "video_chat_url",
            "status",
            "time_asked",
            "asked_by",
            "time_response_started",
            "time_responded_to",
            "responded_to_by",
            "rejected_reason",
            "should_send_up_soon_notification",
            "tags",
            "note",
            "resolved_note",
            "position",
            "student_descriptor",
        )
        read_only_fields = (
            "time_asked",
            "asked_by",
            "time_response_started",
            "time_responded_to",
            "responded_to_by",
            "should_send_up_soon_notification",
            "resolved_note",
            "position",
        )

    def update(self, instance, validated_data):
        """
        Students can update their question's text and video_chat_url or withdraw the question
        TAs+ can only modify the status of a question.
        """
        user = self.context["request"].user
        membership = Membership.objects.get(course=instance.queue.course, user=user)
        queue_id = self.context["view"].kwargs["queue_pk"]

        if membership.is_ta:  # User is a TA+
            if "status" in validated_data:
                status = validated_data["status"]
                if status == Question.STATUS_WITHDRAWN:
                    raise serializers.ValidationError(
                        detail={"detail": "TAs can't mark a question as withdrawn"}
                    )
                instance.status = status
                if status == Question.STATUS_ACTIVE:
                    instance.responded_to_by = user
                    instance.time_response_started = timezone.now()
                elif status == Question.STATUS_REJECTED:
                    instance.responded_to_by = user
                    instance.time_response_started = timezone.now()
                    instance.time_responded_to = timezone.now()
                    instance.rejected_reason = validated_data["rejected_reason"]
                    sendUpNextNotificationTask.delay(queue_id)
                elif status == Question.STATUS_ANSWERED:
                    instance.time_responded_to = timezone.now()
                    sendUpNextNotificationTask.delay(queue_id)
                elif status == Question.STATUS_ASKED:
                    instance.responded_to_by = None
                    instance.time_response_started = None
            if "note" in validated_data:
                instance.note = validated_data["note"]
                instance.resolved_note = False
        else:  # User is a student
            if "status" in validated_data:
                status = validated_data["status"]
                if status == Question.STATUS_WITHDRAWN:
                    instance.status = status
                    sendUpNextNotificationTask.delay(queue_id)
                elif status == Question.STATUS_ANSWERED:
                    instance.status = status
                    instance.time_responded_to = timezone.now()
                else:
                    raise serializers.ValidationError(
                        detail={"detail": "Students can only withdraw a question"}
                    )
            if "text" in validated_data:
                instance.text = validated_data["text"]
            if "video_chat_url" in validated_data:
                instance.video_chat_url = validated_data["video_chat_url"]
            if "tags" in validated_data:
                instance.tags.clear()
                for tag_data in validated_data.pop("tags"):
                    try:
                        tag = Tag.objects.get(course=instance.queue.course, **tag_data)
                        instance.tags.add(tag)
                    except ObjectDoesNotExist:
                        continue
            if "student_descriptor" in validated_data:
                instance.student_descriptor = validated_data["student_descriptor"]
            # If a student modifies a question, discard any note added by a TA and mark as resolved
            instance.note = ""
            instance.resolved_note = True

        instance.save()

        # if the status changes to something that affects position, call save() on asked questions
        if "status" in validated_data:
            asked_questions = Question.objects.filter(
                queue=instance.queue, status=Question.STATUS_ASKED
            )

            for question in asked_questions:
                save_handler(sender=Question, instance=question, dispatch_uid="rest-live")

        return instance

    def create(self, validated_data):
        tags = validated_data.pop("tags")
        queue = Queue.objects.get(pk=self.context["view"].kwargs["queue_pk"])
        questions_ahead = Question.objects.filter(
            queue=queue, status=Question.STATUS_ASKED, time_asked__lt=timezone.now()
        ).count()
        validated_data["should_send_up_soon_notification"] = questions_ahead >= 4
        validated_data["status"] = Question.STATUS_ASKED
        validated_data["asked_by"] = self.context["request"].user
        question = super().create(validated_data)
        for tag_data in tags:
            try:
                tag = Tag.objects.get(course=queue.course, **tag_data)
                question.tags.add(tag)
            except ObjectDoesNotExist:
                continue
        return question


class MembershipPrivateSerializer(CourseRouteMixin):
    """
    Private serializer that contains course information
    """

    course = CourseSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "course", "kind", "time_created", "last_active")


class ProfileSerializer(serializers.ModelSerializer):
    phone_number = PhoneNumberField()

    class Meta:
        model = Profile
        fields = (
            "sms_notifications_enabled",
            "sms_verified",
            "sms_verification_code",
            "phone_number",
        )
        extra_kwargs = {"sms_verification_code": {"write_only": True}}


class UserPrivateSerializer(serializers.ModelSerializer):
    """
    Private serializer to allow users to see/modify their profiles.
    """

    profile = ProfileSerializer(read_only=False, required=False)
    membership_set = MembershipPrivateSerializer(many=True, read_only=True)
    groups = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "username",
            "profile",
            "membership_set",
            "groups",
        )

    def update(self, instance, validated_data):
        if "profile" in validated_data:
            profile_fields = validated_data.pop("profile")
            profile = instance.profile
            # Set sms notifications enabled
            if "sms_notifications_enabled" in profile_fields:
                profile.sms_notifications_enabled = profile_fields["sms_notifications_enabled"]

            # Handle new phone number
            if (
                "phone_number" in profile_fields
                and profile_fields["phone_number"] != profile.phone_number
            ):
                profile.phone_number = profile_fields["phone_number"]
                profile.sms_verified = False
                profile.sms_verification_code = get_random_string(
                    length=6, allowed_chars="1234567890"
                )
                profile.sms_verification_timestamp = timezone.now()
                sendSMSVerification(profile.phone_number, profile.sms_verification_code)

            # Handle SMS verification
            if "sms_verification_code" in profile_fields:
                elapsed_time = timezone.now() - profile.sms_verification_timestamp
                if (
                    profile_fields["sms_verification_code"] == profile.sms_verification_code
                    and elapsed_time.total_seconds()
                    < Profile.SMS_VERIFICATION_EXPIRATION_MINUTES * 60
                ):
                    profile.sms_verified = True
                elif (
                    elapsed_time.total_seconds() >= Profile.SMS_VERIFICATION_EXPIRATION_MINUTES * 60
                ):
                    raise serializers.ValidationError(
                        detail={"detail": "Verification code has expired"}
                    )
                else:
                    raise serializers.ValidationError(
                        detail={"detail": "Incorrect verification code"}
                    )

            profile.save()
        return super().update(instance, validated_data)


class CourseStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseStatistic
        fields = ("user", "metric", "value", "date")
        # make everything read-only, stats are only updated through commands
        read_only_fields = ("user", "metric", "value", "date")


class QueueStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueStatistic
        fields = ("metric", "day", "hour", "value", "date")
        # make everything read-only, stats are only updated through commands
        read_only_fields = ("metric", "day", "hour", "value", "date")


class AnnouncementSerializer(CourseRouteMixin):
    """
    Serializer for announcements
    """

    author = UserSerializer(read_only=True)

    class Meta:
        model = Announcement
        fields = ("id", "content", "author", "time_updated")
        read_only_fields = ("author",)

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().update(instance, validated_data)


class RuleSerializer(serializers.ModelSerializer):
    """
    Serializer for rules
    """

    class Meta:
        model = Rule
        fields = ("frequency",)


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for events

    All times are converted to UTC+0
    """

    rule = RuleSerializer(required=False)
    course_id = serializers.IntegerField(required=False)

    class Meta:
        model = Event
        fields = (
            "id",
            "start",
            "end",
            "title",
            "description",
            "rule",
            "end_recurring_period",
            "course_id",
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        course_pk = EventRelation.objects.filter(event=instance).first().object_id
        representation["course_id"] = course_pk
        return representation

    def update(self, instance, validated_data):
        rule = instance.rule
        # if changing start, end, or update, delete all previous occurrences
        if (
            ("start" in validated_data and instance.start != validated_data["start"])
            or ("end" in validated_data and instance.end != validated_data["end"])
            or (
                "end_recurring_period" in validated_data
                and instance.end_recurring_period != validated_data["end_recurring_period"]
            )
            or (
                "rule" in validated_data
                and (rule is None or rule.frequency != validated_data["rule"]["frequency"])
            )
        ):
            if "rule" in validated_data:
                rule, _ = Rule.objects.get_or_create(frequency=validated_data["rule"]["frequency"])
                validated_data.pop("rule")
            Occurrence.objects.filter(event=instance).delete()

        # can never change course_id, client should create a new event instead
        validated_data.pop("course_id")
        super().update(instance, validated_data)

        instance.rule = rule
        instance.save()
        return instance

    def create(self, validated_data):
        course = Course.objects.get(pk=validated_data["course_id"])
        rule = None
        if "rule" in validated_data:
            rule, _ = Rule.objects.get_or_create(frequency=validated_data["rule"]["frequency"])
            validated_data.pop("rule")

        validated_data.pop("course_id")
        default_calendar = Calendar.objects.filter(name="DefaultCalendar").first()
        if default_calendar is None:
            default_calendar = Calendar.objects.create(name="DefaultCalendar")
        validated_data["calendar"] = default_calendar

        # for some reason, super().create() doesn't automatically serialize Rule
        event = super().create(validated_data)
        event.rule = rule
        event.save()

        erm = EventRelationManager()
        erm.create_relation(event=event, content_object=course)
        return event


class OccurrenceSerializer(serializers.ModelSerializer):
    """
    Serializer for occurrence
    """

    event = EventSerializer(read_only=True)

    class Meta:
        model = Occurrence
        fields = ("id", "title", "description", "start", "end", "cancelled", "event")

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ("id", "name", "vector_db")

class VectorDBSerializer(serializers.ModelSerializer):
    class Meta:
        model = VectorDB
        fields = ("id", "name", "course", "time_updated", "top_k")