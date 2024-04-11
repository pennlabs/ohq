import math
import re
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import ValidationError
from django.db.models import (
    Case,
    Count,
    Exists,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    When,
)
from django.forms import model_to_dict
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django_auto_prefetching import prefetch
from django_filters.rest_framework import DjangoFilterBackend
from drf_excel.mixins import XLSXFileMixin
from drf_excel.renderers import XLSXRenderer
from pytz import utc
from rest_framework import filters, generics, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_live.mixins import RealtimeMixin
from schedule.models import Event, EventRelationManager, Occurrence

from ohq.filters import CourseStatisticFilter, QuestionSearchFilter, QueueStatisticFilter
from ohq.invite import parse_and_send_invites
from ohq.models import (
    Announcement,
    Course,
    CourseStatistic,
    LlmSetting,
    Membership,
    MembershipInvite,
    Question,
    Queue,
    QueueStatistic,
    Semester,
    Tag,
)
from ohq.pagination import QuestionSearchPagination
from ohq.permissions import (
    AnnouncementPermission,
    CoursePermission,
    CourseStatisticPermission,
    EventPermission,
    IsSuperuser,
    MassInvitePermission,
    MembershipInvitePermission,
    MembershipPermission,
    OccurrencePermission,
    LlmResponsePermission,
    LlmSettingPermission,
    QuestionPermission,
    QuestionSearchPermission,
    QueuePermission,
    QueueStatisticPermission,
    TagPermission,
)
from ohq.schemas import EventSchema, MassInviteSchema, OccurrenceSchema
from ohq.serializers import (
    AnnouncementSerializer,
    CourseCreateSerializer,
    CourseSerializer,
    CourseStatisticSerializer,
    EventSerializer,
    LlmPromptSerializer,
    MembershipInviteSerializer,
    MembershipSerializer,
    OccurrenceSerializer,
    Profile,
    QuestionSerializer,
    QueueSerializer,
    QueueStatisticSerializer,
    SemesterSerializer,
    TagSerializer,
    UserPrivateSerializer,
)
from ohq.sms import sendSMSVerification
from ohq.llm import generateResponse


User = get_user_model()


class UserView(generics.RetrieveUpdateAPIView):
    """
    get:
    Return information about the logged in user.

    update:
    Update information about the logged in user.
    You must specify all of the fields or use a patch request.

    patch:
    Update information about the logged in user.
    Only updates fields that are passed to the server.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserPrivateSerializer

    def get_object(self):
        return self.request.user


class ResendNotificationView(generics.CreateAPIView):
    """
    update:
    Generate and send a new SMS verification if the current one
    has expired
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserPrivateSerializer

    def get_object(self):
        return self.request.user

    def post(self, request, *args, **kwargs):
        user = self.get_object()
        elapsed_time = timezone.now() - user.profile.sms_verification_timestamp
        if elapsed_time.total_seconds() > Profile.SMS_VERIFICATION_EXPIRATION_MINUTES * 60:
            user.profile.sms_verification_code = get_random_string(
                length=6, allowed_chars="1234567890"
            )
            user.profile.sms_verification_timestamp = timezone.now()
            sendSMSVerification(user.profile.phone_number, user.profile.sms_verification_code)
            user.save()
            return JsonResponse({"detail": "success"})
        return HttpResponseBadRequest()


class CourseViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return a single course with all information fields present.

    list:
    Return a list of courses with partial information for each course.

    create:
    Create a course.

    update:
    Update all fields in the course.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the course.
    Only specify the fields that you want to change.

    destroy:
    Delete a course. Consider marking the course as archived instead of deleting the course.
    """

    permission_classes = [CoursePermission | IsSuperuser]
    serializer_class = CourseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["course_code", "department", "course_title"]

    def get_serializer_class(self):
        if self.action == "create":
            return CourseCreateSerializer
        return self.serializer_class

    def get_queryset(self):
        is_member = Membership.objects.filter(course=OuterRef("pk"), user=self.request.user)
        qs = (
            Course.objects.filter(Q(invite_only=False) | Q(membership__user=self.request.user))
            .distinct()
            .annotate(is_member=Exists(is_member))
        )
        return prefetch(qs, self.get_serializer_class())


class QuestionViewSet(viewsets.ModelViewSet, RealtimeMixin):
    """
    retrieve:
    Return a single question with all information fields present.

    list:
    Return a list of questions specific to a queue.
    Students can only see questions they submitted.

    create:
    Create a question.

    update:
    Update all fields in the question.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the question.
    Only specify the fields that you want to change.

    destroy:
    Delete a question.
    """

    permission_classes = [QuestionPermission | IsSuperuser]
    serializer_class = QuestionSerializer
    queryset = Question.objects.none()

    def get_queryset(self):
        position = (
            Question.objects.filter(
                Q(queue=OuterRef("queue"))
                & Q(status=Question.STATUS_ASKED)
                & Q(time_asked__lte=OuterRef("time_asked"))
            )
            .values("queue")
            .annotate(count=Count("queue", output_field=IntegerField()))
            .values("count")
        )

        qs = (
            Question.objects.filter(
                Q(queue=self.kwargs["queue_pk"])
                & (Q(status=Question.STATUS_ASKED) | Q(status=Question.STATUS_ACTIVE))
            )
            .annotate(
                position=Case(
                    When(
                        status=Question.STATUS_ASKED,
                        then=Subquery(position[:1]),
                    ),
                    default=-1,
                )
            )
            .order_by("time_asked")
        )

        membership = Membership.objects.get(course=self.kwargs["course_pk"], user=self.request.user)

        if not membership.is_ta:
            qs = qs.filter(asked_by=self.request.user)
        return prefetch(qs, self.serializer_class)

    @action(detail=True)
    def position(self, request, course_pk, queue_pk, pk=None):
        """
        Get the position of a question within its queue.
        """
        question = self.get_object()
        position = -1
        if question.status == Question.STATUS_ASKED:
            position = (
                Question.objects.filter(
                    queue=queue_pk, status=Question.STATUS_ASKED, time_asked__lt=question.time_asked
                ).count()
                + 1
            )
        return JsonResponse({"position": position})

    @action(detail=False)
    def last(self, request, course_pk, queue_pk):
        """
        Get the last question you asked in a queue. Only visible to Students.
        """

        queryset = Question.objects.filter(
            Q(queue=queue_pk)
            & Q(asked_by=request.user)
            & (
                Q(status=Question.STATUS_WITHDRAWN)
                | Q(status=Question.STATUS_REJECTED)
                | Q(status=Question.STATUS_ANSWERED)
            )
        ).order_by("-time_asked")[:1]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """
        Update a staff member's last active time when they view questions
        """

        membership = Membership.objects.get(user=request.user, course=self.kwargs["course_pk"])
        membership.last_active = timezone.now()
        membership.save()
        return super().list(request, *args, **kwargs)

    def quota_count_helper(self, queue, user):
        """
        Helper to get the questions within the quota period for queues with quotas
        """

        return Question.objects.filter(
            queue=queue,
            asked_by=user,
            time_responded_to__gte=timezone.now() - timedelta(minutes=queue.rate_limit_minutes),
        ).exclude(status__in=[Question.STATUS_REJECTED, Question.STATUS_WITHDRAWN])

    def create(self, request, *args, **kwargs):
        """
        Create a new question and check if it follows the rate limit
        """
        queue = Queue.objects.get(id=self.kwargs["queue_pk"])
        if (
            queue.rate_limit_enabled
            and Question.objects.filter(queue=queue, status=Question.STATUS_ASKED).count()
            >= queue.rate_limit_length
        ):
            num_questions_asked = self.quota_count_helper(queue, request.user).count()

            if num_questions_asked >= queue.rate_limit_questions:
                return JsonResponse({"detail": "rate limited"}, status=429)
        if queue.pin_enabled and queue.pin != request.data.get("pin"):
            return JsonResponse({"detail": "incorrect pin"}, status=409)

        return super().create(request, *args, **kwargs)
    

    @action(detail=False)
    def quota_count(self, request, course_pk, queue_pk):
        """
        Get number of questions asked within rate limit period if it is set up for the queue
        """

        queue = Queue.objects.get(id=queue_pk)
        if queue.rate_limit_enabled:
            questions = self.quota_count_helper(queue, request.user)
            count = questions.count()

            wait_time_mins = 0
            if (
                Question.objects.filter(queue=queue, status=Question.STATUS_ASKED).count()
                >= queue.rate_limit_length
                and count >= queue.rate_limit_questions
            ):
                last_question = questions.order_by("-time_responded_to")[
                    queue.rate_limit_questions - 1
                ]
                wait_time_secs = (
                    queue.rate_limit_minutes * 60
                    - (timezone.now() - last_question.time_responded_to).total_seconds()
                )
                wait_time_mins = math.ceil(wait_time_secs / 60)

            return JsonResponse({"count": count, "wait_time_mins": wait_time_mins})
        else:
            return JsonResponse({"detail": "queue does not have rate limit"}, status=405)


class QuestionSearchView(XLSXFileMixin, generics.ListAPIView):
    filter_backends = [DjangoFilterBackend]
    filterset_class = QuestionSearchFilter
    pagination_class = QuestionSearchPagination
    permission_classes = [QuestionSearchPermission | IsSuperuser]
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [XLSXRenderer]
    serializer_class = QuestionSerializer
    filename = "questions.xlsx"

    def get_queryset(self):
        qs = Question.objects.filter(
            queue__in=Queue.objects.filter(course=self.kwargs["course_pk"])
        ).order_by("time_asked")
        return prefetch(qs, self.serializer_class)

    @property
    def paginator(self):
        """
        Removes pagination from the XLSX Render so that TAs can download a full list
        of asked questions.
        https://www.django-rest-framework.org/api-guide/renderers/#varying-behaviour-by-media-type
        """

        if self.request.accepted_renderer.format == "xlsx":  # xlsx download
            self._paginator = None
            return None
        return super().paginator


class QueueViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return a single queue.

    list:
    Return a list of queues specific to a course.

    create:
    Create a queue.

    update:
    Update all fields in the queue.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the queue.
    Only specify the fields that you want to change.

    destroy:
    Delete a queue.
    """

    permission_classes = [QueuePermission | IsSuperuser]
    serializer_class = QueueSerializer

    def get_queryset(self):
        """
        Annotate the number of questions asked, number of questioned currently being answered,
        and the number of active staff members.
        Filter/annotation pattern taken from here:
        https://stackoverflow.com/questions/42543978/django-1-11-annotating-a-subquery-aggregate
        """

        questions = (
            Question.objects.filter(queue=OuterRef("pk"))
            .order_by()
            .values("queue")
            .annotate(count=Count("*"))
            .values("count")
        )
        questions_active = questions.filter(status=Question.STATUS_ACTIVE)
        questions_asked = questions.filter(status=Question.STATUS_ASKED)

        time_threshold = timezone.now() - timedelta(minutes=1)
        staff_active = (
            Membership.objects.filter(
                Q(course=OuterRef("course__pk"))
                & ~Q(kind=Membership.KIND_STUDENT)
                & Q(last_active__gt=time_threshold)
            )
            .order_by()
            .values("course")
            .annotate(
                count=Count("*", output_field=FloatField()),
            )
            .values("count")
        )

        qs = (
            Queue.objects.filter(course=self.kwargs["course_pk"], archived=False)
            .annotate(
                questions_active=Subquery(questions_active[:1], output_field=IntegerField()),
                questions_asked=Subquery(questions_asked[:1]),
                staff_active=Subquery(staff_active[:1]),
            )
            .order_by("id")
        )

        return prefetch(qs, self.serializer_class)

    @action(methods=["POST"], detail=True)
    def clear(self, request, course_pk, pk=None):
        """
        Clear the queue by rejecting all questions which are currently open (in the asked state).
        """
        queue = self.get_object()
        Question.objects.filter(queue=queue, status=Question.STATUS_ASKED).update(
            status=Question.STATUS_REJECTED,
            rejected_reason="OH_ENDED",
            responded_to_by=self.request.user,
        )
        return JsonResponse({"detail": "success"})


class TagViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return a single tag with all information fields present.

    list:
    Return a list of tags specific to a course.

    create:
    Create a tag.

    update:
    Update all fields in the tag.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the tag.
    Only specify the fields that you want to change.

    destroy:
    Delete a tag.
    """

    permission_classes = [TagPermission | IsSuperuser]
    serializer_class = TagSerializer

    def get_queryset(self):
        qs = Tag.objects.filter(course=self.kwargs["course_pk"])
        return prefetch(qs, self.serializer_class)


class MembershipViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return a single membership.

    list:
    Return a list of memberships specific to a course. Students cannot see
    if peers are members or not.

    create:
    Create a membership.

    update:
    Update all fields in the membership.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the membership.
    Only specify the fields that you want to change.

    destroy:
    Delete a membership.
    """

    permission_classes = [MembershipPermission | IsSuperuser]
    serializer_class = MembershipSerializer

    def get_queryset(self):
        qs = Membership.objects.filter(course=self.kwargs["course_pk"]).order_by("user__first_name")

        membership = Membership.objects.get(course=self.kwargs["course_pk"], user=self.request.user)

        if not membership.is_ta:
            qs = qs.filter(
                Q(kind=Membership.KIND_PROFESSOR)
                | Q(kind=Membership.KIND_HEAD_TA)
                | Q(user=self.request.user)
            )
        return prefetch(qs, self.serializer_class)


class MembershipInviteViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return a single membership invite.

    list:
    Return a list of membership invites specific to a course.

    create:
    Create a membership invite.

    update:
    Update all fields in the membership invite.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the membership invite.
    Only specify the fields that you want to change.

    destroy:
    Delete a membership invite.
    """

    permission_classes = [MembershipInvitePermission | IsSuperuser]
    serializer_class = MembershipInviteSerializer

    def get_queryset(self):
        return MembershipInvite.objects.filter(course=self.kwargs["course_pk"])


class SemesterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:
    Get all semesters

    retrieve:
    Get a specific semester
    """

    serializer_class = SemesterSerializer
    queryset = Semester.objects.all()


class MassInviteView(APIView):
    """
    Sends out invitations to join a course to multiple recipients.
    """

    permission_classes = [MassInvitePermission | IsSuperuser]
    schema = MassInviteSchema()

    def post(self, request, course_pk, format=None):
        kind = request.data.get("kind")
        course = Course.objects.get(id=self.kwargs["course_pk"])
        # Get list of emails
        emails = [x.strip() for x in re.split("\n|,", request.data.get("emails", ""))]
        emails = [x for x in emails if x]

        try:
            members_added, invites_sent = parse_and_send_invites(course, emails, kind)
        except ValidationError:
            return Response({"detail": "invalid emails"}, status=400)

        return Response(
            data={
                "detail": "success",
                "members_added": members_added,
                "invites_sent": invites_sent,
            },
            status=201,
        )


class CourseStatisticView(generics.ListAPIView):
    """
    Return a list of statistics - multiple data points for list statistics and heatmap statistics
    and singleton for card statistics.
    """

    serializer_class = CourseStatisticSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CourseStatisticFilter
    permission_classes = [CourseStatisticPermission | IsSuperuser]

    def get_queryset(self):
        qs = CourseStatistic.objects.filter(course=self.kwargs["course_pk"])
        return prefetch(qs, self.serializer_class)


class QueueStatisticView(generics.ListAPIView):
    """
    Return a list of statistics - multiple data points for list statistics and heatmap statistics
    and singleton for card statistics.
    """

    serializer_class = QueueStatisticSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueStatisticFilter
    permission_classes = [QueueStatisticPermission | IsSuperuser]

    def get_queryset(self):
        # might need to change qs if students shouldn't be able to see all queue statistics
        qs = QueueStatistic.objects.filter(queue=self.kwargs["queue_pk"])
        return prefetch(qs, self.serializer_class)


class AnnouncementViewSet(viewsets.ModelViewSet, RealtimeMixin):
    """
    retrieve:
    Return a single announcement.

    list:
    Return a list of announcements specific to a course.

    create:
    Create a announcement.

    update:
    Update all fields in the announcement.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the announcement.
    Only specify the fields that you want to change.

    destroy:
    Delete a announcement.
    """

    permission_classes = [AnnouncementPermission | IsSuperuser]
    serializer_class = AnnouncementSerializer
    queryset = Announcement.objects.none()

    def get_queryset(self):
        return Announcement.objects.filter(course=self.kwargs["course_pk"])


class EventViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return an event.
    eventId is required

    list:
    Return a list of events associated with a course.

    create:
    Create a event.
    courseId is required in body

    update:
    Update all fields in the event.
    You must specify all of the fields or use a patch request.
    courseId is required in post body for authentication

    partial_update:
    Update certain fields in the event.
    You can update the rule's frequency, but cannot make a reoccurring event happen only once.
    courseId is required in post body for authentication

    destroy:
    Delete an event.
    eventId is required
    """

    serializer_class = EventSerializer
    # permission_classes = [EventPermission | IsSuperuser]
    schema = EventSchema()

    def list(self, request, *args, **kwargs):
        course_ids = request.GET.getlist("course")
        courses = Course.objects.filter(pk__in=course_ids)
        erm = EventRelationManager()

        events = []
        for course in courses:
            events_for_course = erm.get_events_for_object(course)
            for event in events_for_course:
                events.append(event)

        serializer = EventSerializer(events, many=True)
        return JsonResponse(serializer.data, safe=False)

    def get_queryset(self):
        return Event.objects.filter(pk=self.kwargs["pk"])


class OccurrenceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    retrieve:
    Return an Occurrence.

    list:
    You should pass in a list of course ids, along with the filter start and end dates,
    and all the occurrences related to those courses will be returned to you.
    Return a list of Occurrences.

    update:
    Update all fields in an Occurrence.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the Occurrece.
    """

    serializer_class = OccurrenceSerializer
    # permission_classes = [OccurrencePermission | IsSuperuser]
    schema = OccurrenceSchema()

    def list(self, request, *args, **kwargs):
        # ensure timezone consitency
        course_ids = request.GET.getlist("course")
        filter_start = datetime.strptime(
            request.GET.get("filter_start"), "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=utc)
        filter_end = datetime.strptime(request.GET.get("filter_end"), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=utc
        )
        courses = Course.objects.filter(pk__in=course_ids)
        erm = EventRelationManager()
        occurrences = []
        for course in courses:
            events_for_course = erm.get_events_for_object(course)
            for event in events_for_course:
                for occurrence in event.get_occurrences(filter_start, filter_end):
                    # need to save because get_occurrences only create temporary Occurrence objs
                    # once we save the Occurrence objs, later calls will retrieve them,
                    # and no duplicates will be created
                    occurrence.save()
                    occurrences.append(occurrence)

        serializer = OccurrenceSerializer(occurrences, many=True)
        return JsonResponse(serializer.data, safe=False)

    def get_queryset(self):
        return Occurrence.objects.filter(pk=self.kwargs["pk"])

class LlmSettingViewSet(viewsets.ModelViewSet, RealtimeMixin):
    """
    retrieve:
    Return a prompt.

    list:
    Return a list of prompts specific to a queue.
    Students can only see prompts they submitted.

    create:
    Create a prompt.

    update:
    Update all fields in the prompt.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the prompt.
    Only specify the fields that you want to change.

    destroy:
    Delete a prompt.
    """
    permission_classes = [LlmSettingPermission | IsSuperuser]
    serializer_class = LlmPromptSerializer

    def get_queryset(self):
        return LlmSetting.objects.filter(course=self.kwargs["course_pk"])
    
    def create(self, request, *args, **kwargs):
        "Create a new LLM Prompt"
        queryset = Course.objects.filter(pk=self.kwargs["course_pk"])
        request.data["course"] = self.kwargs["course_pk"]
        course = queryset[0]

        prompt = str(settings.BASE_LLM_PROMPT)
        prompt = prompt.replace("\\course.department\\", course.department)
        prompt = prompt.replace("\\course.course_code\\", course.course_code)
        prompt = prompt.replace("\\course.course_title\\", course.course_title)
        prompt = prompt.replace("\\course.description\\", course.description)
        
        request.data["llm_prompt"] = prompt + "\n" + request.data["llm_prompt"]
        return super().create(request, *args, **kwargs)
    
    def patch(self, request, *args, **kwargs):
        if "llm_prompt" in request.data:
            return JsonResponse(data="Please do not change template prompt")
        obj = LlmSetting.objects.filter(course=self.kwargs["course_pk"])[0]
        serializer = LlmPromptSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(data=model_to_dict(obj))
        return JsonResponse(data="wrong parameters")

class LlmResponseViewSet(viewsets.ModelViewSet, generics.ListAPIView):
    """
    retrieve:
    Return a response.

    list:
    Return a list of response specific to a queue.
    Students can only see response to the questions they submitted.

    create:
    Create a response.

    update:
    Update all fields in the response.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the response.
    Only specify the fields that you want to change.

    destroy:
    Delete a response.
    """

    permission_classes = [LlmResponsePermission | IsSuperuser]
    serializer_class = QuestionSerializer

    def get_queryset(self, *args, **kwargs):
        return Question.objects.filter(pk=self.kwargs['question_pk'])

    def create(self, *args, **kwargs):
        """
        Create a new response if not yet created
        """

        question = Question.objects.filter(pk=self.kwargs['question_pk'])
        
        items = LlmSetting.objects.filter(course_id=self.kwargs['course_pk'])
    
        response = generateResponse(question[0].text, items[0])
        QuestionSerializer.update(self, question[0], {
            "llm_response": response
        })
        return JsonResponse({"response": response})
    