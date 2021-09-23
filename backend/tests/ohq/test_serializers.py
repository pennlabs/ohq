from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.test import APIClient

from ohq.models import Announcement, Course, Membership, Question, Queue, Semester, Tag
from ohq.serializers import (
    CourseCreateSerializer,
    MembershipSerializer,
    SemesterSerializer,
    UserPrivateSerializer,
)


User = get_user_model()


class UserPrivateSerializerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user")
        self.serializer = UserPrivateSerializer(instance=self.user)

    def test_set_sms_notifications_enabled(self):
        self.assertFalse(self.user.profile.sms_notifications_enabled)
        self.serializer.update(self.user, {"profile": {"sms_notifications_enabled": True}})
        self.assertTrue(self.user.profile.sms_notifications_enabled)

    def test_set_new_phone_number(self):
        self.assertIsNone(self.user.profile.sms_verification_timestamp)
        phone_number = "+15555555555"
        self.serializer.update(self.user, {"profile": {"phone_number": phone_number}})
        self.assertFalse(self.user.profile.sms_verified)
        self.assertEqual(self.user.profile.phone_number, phone_number)
        self.assertIsNotNone(self.user.profile.sms_verification_timestamp)
        self.assertRegex(self.user.profile.sms_verification_code, "[0-9]{6}")

    def test_verify_phone_number(self):
        self.serializer.update(self.user, {"profile": {"phone_number": "+15555555555"}})
        self.serializer.update(
            self.user,
            {"profile": {"sms_verification_code": self.user.profile.sms_verification_code}},
        )
        self.assertTrue(self.user.profile.sms_verified)

    def test_verify_phone_number_invalid(self):
        self.serializer.update(self.user, {"profile": {"phone_number": "+15555555555"}})
        with self.assertRaises(serializers.ValidationError):
            self.serializer.update(
                self.user, {"profile": {"sms_verification_code": "ABC123"}},
            )

    def test_verify_phone_number_time_expired(self):
        self.serializer.update(self.user, {"profile": {"phone_number": "+15555555555"}})
        date = timezone.make_aware(datetime(2020, 1, 1))
        self.user.profile.sms_verification_timestamp = date
        with self.assertRaises(serializers.ValidationError):
            self.serializer.update(
                self.user,
                {"profile": {"sms_verification_code": self.user.profile.sms_verification_code}},
            )


class CourseCreateSerializerTestCase(TestCase):
    def test_create_membership(self):
        semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        user = User.objects.create(username="user")
        data = {
            "course_code": "000",
            "department": "Penn Labs",
            "course_title": "Course",
            "semester": semester.id,
            "created_role": Membership.KIND_HEAD_TA,
        }

        request = RequestFactory().get("/")
        request.user = user
        serializer = CourseCreateSerializer(data=data, context={"request": request})
        serializer.is_valid()
        serializer.save()
        self.assertEqual(1, len(Membership.objects.all()))
        membership = Membership.objects.get(user=user)
        self.assertEqual(membership.kind, Membership.KIND_HEAD_TA)


class MembershipSerializerTestCase(TestCase):
    def test_create_membership(self):
        semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        course = Course.objects.create(course_code="000", department="Penn Labs", semester=semester)

        user = User.objects.create(username="professor")

        class View(object):
            """
            Mock view object to provide a course pk
            """

            def __init__(self):
                self.kwargs = {"course_pk": course.id}

        request = RequestFactory().get("/")
        request.user = user
        serializer = MembershipSerializer(data={}, context={"request": request, "view": View()})
        serializer.is_valid()
        serializer.save()
        self.assertEqual(1, len(Membership.objects.all()))


class SemesterSerializerTestCase(TestCase):
    def test_pretty(self):
        semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        serializer = SemesterSerializer(instance=semester)
        self.assertEqual(serializer.data["pretty"], str(semester))


class QueueSerializerTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
            course_code="000", department="Penn Labs", semester=self.semester
        )
        self.name = "Queue"
        self.queue = Queue.objects.create(name=self.name, course=self.course)
        self.head_ta = User.objects.create(username="head_ta")
        self.ta = User.objects.create(username="ta")
        Membership.objects.create(
            course=self.course, user=self.head_ta, kind=Membership.KIND_HEAD_TA
        )
        Membership.objects.create(course=self.course, user=self.ta, kind=Membership.KIND_TA)

    def test_update_active_ta(self):
        """
        Ensure TAs can open and close a queue.
        """

        self.assertFalse(self.queue.active)
        self.client.force_authenticate(user=self.ta)
        self.client.patch(
            reverse("ohq:queue-detail", args=[self.course.id, self.queue.id]), {"active": True}
        )
        self.queue.refresh_from_db()
        self.assertTrue(self.queue.active)

    def test_update_other_ta(self):
        """
        TAs can't modify other attributes of a queue
        """

        self.assertEqual(self.name, self.queue.name)
        self.client.force_authenticate(user=self.ta)
        self.client.patch(
            reverse("ohq:queue-detail", args=[self.course.id, self.queue.id]), {"name": "New"}
        )
        self.queue.refresh_from_db()
        self.assertEqual(self.name, self.queue.name)

    def test_update_leadership(self):
        """
        Course leadership can modify anything
        """

        self.assertEqual(self.name, self.queue.name)
        self.client.force_authenticate(user=self.head_ta)
        new_name = "New Queue Name"
        self.client.patch(
            reverse("ohq:queue-detail", args=[self.course.id, self.queue.id]), {"name": new_name}
        )
        self.queue.refresh_from_db()
        self.assertEqual(new_name, self.queue.name)


@patch("ohq.serializers.sendUpNextNotificationTask.delay")
class QuestionSerializerTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
            course_code="000", department="Penn Labs", semester=self.semester
        )
        self.course2 = Course.objects.create(
            course_code="001", department="Penn Labs", semester=self.semester
        )
        self.queue = Queue.objects.create(name="Queue", course=self.course)
        self.queue2 = Queue.objects.create(name="Queue", course=self.course2)
        self.ta = User.objects.create(username="ta")
        self.student = User.objects.create(username="student")
        self.student2 = User.objects.create(username="student2")
        Tag.objects.create(course=self.course, name="Tag")
        Tag.objects.create(course=self.course2, name="Tag")
        Membership.objects.create(course=self.course, user=self.ta, kind=Membership.KIND_TA)
        Membership.objects.create(
            course=self.course, user=self.student, kind=Membership.KIND_STUDENT
        )
        Membership.objects.create(
            course=self.course, user=self.student2, kind=Membership.KIND_STUDENT
        )
        self.question_text = "This is a question"
        self.question = Question.objects.create(
            queue=self.queue, asked_by=self.student, text=self.question_text
        )

    def test_create(self, mock_delay):
        self.client.force_authenticate(user=self.student2)
        self.client.post(
            reverse("ohq:question-list", args=[self.course.id, self.queue.id]),
            {"text": "Help me", "tags": [{"name": "Tag"}]},
        )
        self.assertEqual(2, Question.objects.all().count())
        question = Question.objects.all().order_by("time_asked")[1]
        self.assertEqual(self.student2, question.asked_by)
        self.assertEqual(Question.STATUS_ASKED, question.status)
        mock_delay.assert_not_called()

    def test_student_update(self, mock_delay):
        """
        Ensure a student can update their question's text and videochat link.
        """

        text = "Different"
        url = "https://example.com"
        student_descriptor = "In the back"
        self.client.force_authenticate(user=self.student)
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {
                "text": text,
                "video_chat_url": url,
                "tags": [{"name": "Tag"}],
                "student_descriptor": student_descriptor,
            },
        )
        self.question.refresh_from_db()
        self.assertEqual(text, self.question.text)
        self.assertEqual(url, self.question.video_chat_url)
        self.assertEqual(student_descriptor, self.question.student_descriptor)
        mock_delay.assert_not_called()

    def test_student_update_note(self, mock_delay):
        """
        Ensure a note is removed when a student modifies their question.
        """

        self.question.note = "Make changes"
        self.question.resolved_note = False
        self.question.save()
        self.client.force_authenticate(user=self.student)
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"text": "different"},
        )
        self.question.refresh_from_db()
        self.assertTrue(self.question.resolved_note)
        self.assertEqual(self.question.note, "")
        mock_delay.assert_not_called()

    def test_student_withdraw(self, mock_delay):
        """
        Ensure a student can withdraw their question.
        """

        self.client.force_authenticate(user=self.student)
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": Question.STATUS_WITHDRAWN},
        )
        self.question.refresh_from_db()
        self.assertEqual(Question.STATUS_WITHDRAWN, self.question.status)
        mock_delay.assert_called()

    def test_student_active(self, mock_delay):
        """
        Ensure students can't mark a question as active
        """

        self.client.force_authenticate(user=self.student)
        response = self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": Question.STATUS_ACTIVE},
        )
        self.assertEqual(400, response.status_code)
        self.question.refresh_from_db()
        self.assertEqual(Question.STATUS_ASKED, self.question.status)
        mock_delay.assert_not_called()

    def test_student_answered(self, mock_delay):
        """
        Ensure a student can mark their question as answered
        """

        self.client.force_authenticate(user=self.student)
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": Question.STATUS_ANSWERED},
        )
        self.question.refresh_from_db()
        self.assertEqual(Question.STATUS_ANSWERED, self.question.status)
        mock_delay.assert_not_called()

    def test_ta_update(self, mock_delay):
        """
        Ensure TAs+ can start answering, undo answering, and reject a question
        """

        self.client.force_authenticate(user=self.ta)
        # Start answering the question
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": Question.STATUS_ACTIVE},
        )
        self.question.refresh_from_db()
        self.assertEqual(Question.STATUS_ACTIVE, self.question.status)
        self.assertEqual(self.ta, self.question.responded_to_by)
        # Add a note to the question
        note = "Invalid zoom link"
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"note": note},
        )
        self.question.refresh_from_db()
        self.assertFalse(self.question.resolved_note)
        self.assertEqual(self.question.note, note)

        # Undo and put user back in queue
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": Question.STATUS_ASKED},
        )
        self.question.refresh_from_db()
        self.assertEqual(Question.STATUS_ASKED, self.question.status)
        self.assertIsNone(self.question.responded_to_by)
        # Reject the question
        rejected_reason = "This is a rejection"
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": Question.STATUS_REJECTED, "rejected_reason": rejected_reason},
        )
        self.question.refresh_from_db()
        self.assertEqual(Question.STATUS_REJECTED, self.question.status)
        self.assertEqual(self.ta, self.question.responded_to_by)
        self.assertEqual(rejected_reason, self.question.rejected_reason)
        mock_delay.assert_called()

    def test_ta_answer(self, mock_delay):
        """
        Ensure TAs+ can answer a question
        """

        self.client.force_authenticate(user=self.ta)
        # Start answering the question
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": Question.STATUS_ACTIVE},
        )
        self.question.refresh_from_db()
        self.assertEqual(Question.STATUS_ACTIVE, self.question.status)
        self.assertEqual(self.ta, self.question.responded_to_by)
        # Finish answering the question
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": Question.STATUS_ANSWERED},
        )
        self.question.refresh_from_db()
        self.assertEqual(Question.STATUS_ANSWERED, self.question.status)
        self.assertEqual(self.ta, self.question.responded_to_by)
        mock_delay.assert_called()

    def test_ta_update_text(self, mock_delay):
        """
        Ensure TAs+ can't modify a question's contents
        """

        self.client.force_authenticate(user=self.ta)
        response = self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"text": "Different"},
        )
        self.assertEqual(200, response.status_code)
        self.question.refresh_from_db()
        self.assertEqual(self.question_text, self.question.text)
        mock_delay.assert_not_called()

    def test_ta_withdraw(self, mock_delay):
        """
        Ensure TAs+ can't mark a question as withdrawn
        """

        self.client.force_authenticate(user=self.ta)
        response = self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": Question.STATUS_WITHDRAWN},
        )
        self.assertEqual(400, response.status_code)
        self.question.refresh_from_db()
        self.assertEqual(Question.STATUS_ASKED, self.question.status)
        mock_delay.assert_not_called()


class AnnouncementSerializerTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
            course_code="000", department="Penn Labs", semester=self.semester
        )
        self.name = "Queue"
        self.queue = Queue.objects.create(name=self.name, course=self.course)
        self.head_ta = User.objects.create(username="head_ta")
        self.ta = User.objects.create(username="ta")
        Membership.objects.create(
            course=self.course, user=self.head_ta, kind=Membership.KIND_HEAD_TA
        )
        Membership.objects.create(course=self.course, user=self.ta, kind=Membership.KIND_TA)
        self.announcement = Announcement.objects.create(
            course=self.course, author=self.head_ta, content="Original announcement"
        )

    def test_update_ta(self):
        """
        Ensure TAs can update an Announcement and the author is updated
        """
        content = "New content"
        self.client.force_authenticate(user=self.ta)
        self.client.patch(
            reverse("ohq:announcement-detail", args=[self.course.id, self.announcement.id]),
            {"content": content},
        )
        self.announcement.refresh_from_db()
        self.assertTrue(self.announcement.author, self.ta)

    def test_create(self):
        """
        Ensure TAs can create an Announcement and the author matches
        """
        self.client.force_authenticate(user=self.ta)
        self.client.post(
            reverse("ohq:announcement-list", args=[self.course.id]), {"content": "New announcement"}
        )
        self.assertEqual(2, Announcement.objects.all().count())
        announcement = Announcement.objects.all().order_by("time_updated")[1]
        self.assertEqual(self.ta, announcement.author)
