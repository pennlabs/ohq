import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from djangorestframework_camel_case.util import camelize
from rest_framework.test import APIClient
from schedule.models import Event, Occurrence

from ohq.models import Course, Membership, MembershipInvite, Question, Queue, Semester
from ohq.serializers import UserPrivateSerializer


User = get_user_model()


class UserViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username="user")
        self.serializer = UserPrivateSerializer(self.user)

    def test_get_object(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("ohq:me"))
        self.assertEqual(json.loads(response.content), camelize(self.serializer.data))


class ResendNotificationViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username="user")
        self.verification_code = "123456"
        self.user.profile.sms_verification_code = self.verification_code
        self.user.profile.sms_verification_timestamp = timezone.now()

    def test_resend_fail(self):
        """
        Ensure resend fails if sent within 10 minutes.
        """

        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("ohq:resend"))
        self.assertEqual(400, response.status_code)

    def test_resend_success(self):
        """
        Ensure resend works if sent after 10 minutes.
        """

        self.user.profile.sms_verification_timestamp = timezone.now() - timedelta(minutes=11)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("ohq:resend"))
        self.assertEqual(200, response.status_code)
        self.assertNotEqual(self.verification_code, self.user.profile.sms_verification_code)


class MassInviteTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
            course_code="000", department="TEST", course_title="Title", semester=self.semester
        )

        self.professor = User.objects.create(username="professor", email="professor@example.com")
        Membership.objects.create(
            course=self.course, user=self.professor, kind=Membership.KIND_PROFESSOR
        )

        self.user1 = User.objects.create(username="user1", email="user1@example.com")
        Membership.objects.create(course=self.course, user=self.user1, kind=Membership.KIND_STUDENT)

        self.user2 = User.objects.create(username="user2", email="user2@example.com")
        Membership.objects.create(course=self.course, user=self.user2, kind=Membership.KIND_TA)

        self.user3 = User.objects.create(username="user3", email="user3@example.com")

        MembershipInvite.objects.create(
            course=self.course, email="user4@example.com", kind=Membership.KIND_STUDENT
        )

        MembershipInvite.objects.create(
            course=self.course, email="user5@example.com", kind=Membership.KIND_TA
        )

    def test_invalid_email(self):
        self.client.force_authenticate(user=self.professor)
        response = self.client.post(
            reverse("ohq:mass-invite", args=[self.course.id]),
            data={"emails": "invalidemail", "kind": "TA"},
        )
        self.assertEqual(400, response.status_code)

    def test_valid_emails(self):
        self.client.force_authenticate(user=self.professor)
        emails = "user1@example.com,user2@example.com,user3@example.com,user4@example.com,user5@example.com,user6@example.com"
        response = self.client.post(
            reverse("ohq:mass-invite", args=[self.course.id]),
            data={"emails": emails, "kind": "TA"},
        )

        self.assertEqual(201, response.status_code)

        # Correct number of invites and memberships created
        content = json.loads(response.content)
        self.assertEqual(2, content["membersAdded"])
        self.assertEqual(2, content["invitesSent"])


class QuestionViewTestCase(TestCase):
    """
    Tests for the Question ViewSet, especially when it comes to creating questions when the
    queue has a quota and getting the number of questions asked within the quota period
    """

    def setUp(self):
        self.client = APIClient()
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_FALL)
        self.course = Course.objects.create(
            course_code="000", department="Test Class", semester=self.semester
        )
        self.queue = Queue.objects.create(
            name="Queue",
            course=self.course,
            rate_limit_enabled=True,
            rate_limit_length=0,
            rate_limit_minutes=20,
            rate_limit_questions=1,
        )
        self.queue2 = Queue.objects.create(
            name="Queue2",
            course=self.course,
            rate_limit_enabled=True,
            rate_limit_length=0,
            rate_limit_minutes=15,
            rate_limit_questions=2,
        )
        self.queue3 = Queue.objects.create(
            name="Queue3",
            course=self.course,
            rate_limit_enabled=True,
            rate_limit_length=0,
            rate_limit_minutes=15,
            rate_limit_questions=2,
        )
        self.pin = "AAAAA"
        self.pin_queue = Queue.objects.create(
            name="Pin Queue", course=self.course, pin_enabled=True, pin=self.pin
        )
        self.no_limit_queue = Queue.objects.create(name="No Rate Limit Queue", course=self.course)
        self.ta = User.objects.create(username="ta")
        self.student = User.objects.create(username="student")
        self.student2 = User.objects.create(username="student2")
        self.student3 = User.objects.create(username="student3")
        Membership.objects.create(course=self.course, user=self.ta, kind=Membership.KIND_TA)
        Membership.objects.create(
            course=self.course, user=self.student, kind=Membership.KIND_STUDENT
        )
        Membership.objects.create(
            course=self.course, user=self.student2, kind=Membership.KIND_STUDENT
        )
        Membership.objects.create(
            course=self.course, user=self.student3, kind=Membership.KIND_STUDENT
        )
        self.question = Question.objects.create(
            queue=self.queue, asked_by=self.student, text="Help me"
        )
        self.question.time_asked = timezone.now() - timedelta(days=1)
        self.question.save()

        self.old_question = Question.objects.create(
            queue=self.queue,
            asked_by=self.student,
            text="Help me",
            time_responded_to=timezone.now() - timedelta(days=1),
            time_response_started=timezone.now() - timedelta(days=1),
            responded_to_by=self.ta,
            status=Question.STATUS_ANSWERED,
        )
        self.old_question.time_asked = timezone.now() - timedelta(days=1)
        self.old_question.save()
        self.rejected_question = Question.objects.create(
            queue=self.queue,
            asked_by=self.student,
            text="Help me",
            time_responded_to=timezone.now(),
            time_response_started=timezone.now(),
            responded_to_by=self.ta,
            status=Question.STATUS_REJECTED,
        )

        self.prelimit_question = Question.objects.create(
            queue=self.queue2, asked_by=self.student3, text="Help me"
        )
        self.prelimit_question1 = Question.objects.create(
            queue=self.queue2, asked_by=self.student3, text="Help me"
        )
        self.prelimit_question2 = Question.objects.create(
            queue=self.queue2, asked_by=self.student3, text="Help me"
        )

        self.prelimit_question.time_responded_to = timezone.now() - timedelta(minutes=3)
        self.prelimit_question1.time_responded_to = timezone.now() - timedelta(minutes=6)
        self.prelimit_question.save()
        self.prelimit_question1.save()

        Question.objects.create(queue=self.queue3, asked_by=self.student3, text="Help me")

    def test_rate_limit(self):
        self.client.force_authenticate(user=self.student)
        self.client.patch(
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": Question.STATUS_ANSWERED},
        )
        self.assertEqual(7, Question.objects.all().count())

        res = self.client.post(
            reverse("ohq:question-list", args=[self.course.id, self.queue.id]),
            {"text": "Should be rate limited", "tags": []},
        )
        self.assertEqual(429, res.status_code)
        self.assertEqual(7, Question.objects.all().count())

        res = self.client.get(
            reverse("ohq:question-quota-count", args=[self.course.id, self.queue.id])
        )
        self.assertEqual(1, json.loads(res.content)["count"])

        res = self.client.get(
            reverse("ohq:question-quota-count", args=[self.course.id, self.no_limit_queue.id])
        )
        self.assertEqual(405, res.status_code)

        self.client.force_authenticate(user=self.student2)
        self.client.post(
            reverse("ohq:question-list", args=[self.course.id, self.queue.id]),
            {"text": "Shouldn't be rate limited", "tags": []},
        )
        self.assertEqual(8, Question.objects.all().count())

        self.client.force_authenticate(user=self.student3)
        res = self.client.get(
            reverse("ohq:question-quota-count", args=[self.course.id, self.queue2.id])
        )
        self.assertEqual(9, json.loads(res.content)["wait_time_mins"])

        res = self.client.get(
            reverse("ohq:question-quota-count", args=[self.course.id, self.queue3.id])
        )
        self.assertEqual(0, json.loads(res.content)["wait_time_mins"])

    def test_create_with_pin(self):
        self.client.force_authenticate(user=self.student)
        Question.objects.all().delete()

        # correct pin is required in queues with pin_enabled
        self.client.post(
            reverse("ohq:question-list", args=[self.course.id, self.pin_queue.id]),
            {"text": "Help me", "tags": []},
        )
        self.assertEqual(0, Question.objects.all().count())

        self.client.post(
            reverse("ohq:question-list", args=[self.course.id, self.pin_queue.id]),
            {"text": "Help me", "tags": [], "pin": "BBBBB"},
        )
        self.assertEqual(0, Question.objects.all().count())

        self.client.post(
            reverse("ohq:question-list", args=[self.course.id, self.pin_queue.id]),
            {"text": "Help me", "tags": [], "pin": self.pin},
        )
        self.assertEqual(1, Question.objects.all().count())

        # queue without pin enabled does not require pin in post data
        self.client.post(
            reverse("ohq:question-list", args=[self.course.id, self.no_limit_queue.id]),
            {"text": "Help me", "tags": []},
        )
        self.assertEqual(2, Question.objects.all().count())


class OccurrenceViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
            course_code="000", department="Penn Labs", semester=self.semester
        )
        self.head_ta = User.objects.create(username="head_ta")
        self.ta = User.objects.create(username="ta")
        self.student = User.objects.create(username="student")
        Membership.objects.create(
            course=self.course, user=self.head_ta, kind=Membership.KIND_HEAD_TA
        )
        Membership.objects.create(course=self.course, user=self.ta, kind=Membership.KIND_TA)
        Membership.objects.create(
            course=self.course, user=self.student, kind=Membership.KIND_STUDENT
        )
        self.title = "TA session"
        self.start_time = "2021-12-05T12:41:37Z"
        self.end_time = "2021-12-06T12:41:37Z"
        self.end_recurring_period = "2022-12-05T12:41:37Z"
        self.filter_start = "2021-12-05T12:40:37Z"
        self.filter_end = "2021-12-12T12:42:37Z"

    def test_list(self):
        self.client.force_authenticate(user=self.ta)
        self.client.post(
            reverse("ohq:event-list"),
            {
                "start": self.start_time,
                "end": self.end_time,
                "title": self.title,
                "rule": {"frequency": "WEEKLY"},
                "end_recurring_period": self.end_recurring_period,
                "course_id": self.course.id,
            },
        )
        response = self.client.get(
            "/api/occurrences/?course="
            + str(self.course.id)
            + "&filter_start="
            + self.filter_start
            + "&filter_end="
            + self.filter_end
        )
        occurrences = json.loads(response.content)
        self.assertEquals(2, len(occurrences))

    def test_cancel(self):
        self.client.force_authenticate(user=self.ta)
        self.client.post(
            reverse("ohq:event-list"),
            {
                "start": self.start_time,
                "end": self.end_time,
                "title": self.title,
                "end_recurring_period": self.end_recurring_period,
                "course_id": self.course.id,
            },
        )
        event = Event.objects.all().first()
        # create at least one occurrence
        self.client.get(
            "/api/occurrences/?course="
            + str(self.course.id)
            + "&filter_start="
            + self.filter_start
            + "&filter_end="
            + self.filter_end
        )
        occurrence = Occurrence.objects.all().first()
        self.client.patch(
            reverse("ohq:occurrence-detail", args=[occurrence.id]),
            {
                "event": event.id,
                "start": occurrence.start,
                "end": occurrence.end,
                "cancelled": True,
            },
        )
        occurrence = event.get_occurrences(event.start - timedelta(1), event.start + timedelta(1))[
            0
        ]
        self.assertTrue(occurrence.cancelled)

    def test_no_rule(self):
        # events without rule occur only once
        self.client.force_authenticate(user=self.ta)
        self.client.post(
            reverse("ohq:event-list"),
            {
                "start": self.start_time,
                "end": self.end_time,
                "title": self.title,
                "end_recurring_period": self.end_recurring_period,
                "course_id": self.course.id,
            },
        )
        response = self.client.get(
            "/api/occurrences/?course="
            + str(self.course.id)
            + "&filter_start="
            + self.filter_start
            + "&filter_end="
            + self.filter_end
        )
        occurrences = json.loads(response.content)
        self.assertEquals(1, len(occurrences))

        # calling twice doesn't create more occurrences
        response = self.client.get(
            "/api/occurrences/?course="
            + str(self.course.id)
            + "&filter_start="
            + self.filter_start
            + "&filter_end="
            + self.filter_end
        )
        occurrences = json.loads(response.content)
        self.assertEquals(1, len(occurrences))
        cnt = Occurrence.objects.all().count()
        self.assertEquals(1, cnt)

    def test_update_start(self):
        self.client.force_authenticate(user=self.ta)
        self.client.post(
            reverse("ohq:event-list"),
            {
                "start": self.start_time,
                "end": self.end_time,
                "title": self.title,
                "rule": {"frequency": "WEEKLY"},
                "end_recurring_period": self.end_recurring_period,
                "course_id": self.course.id,
            },
        )
        filter_start = "2021-12-04T12:40:37Z"
        filter_end = "2021-12-13T12:40:37Z"
        response = self.client.get(
            "/api/occurrences/?course="
            + str(self.course.id)
            + "&filter_start="
            + filter_start
            + "&filter_end="
            + filter_end
        )
        occurrences = json.loads(response.content)
        self.assertEquals(2, len(occurrences))
        self.assertEquals(occurrences[0]["start"], self.start_time)
        # update event's start day should update occurrences
        event = Event.objects.all().first()
        new_start_date = "2021-12-07T12:40:37Z"
        new_end_date = "2021-12-08T12:40:37Z"
        response = self.client.patch(
            reverse("ohq:event-detail", args=[event.id]),
            {
                "title": "New TA Session",
                "course_id": self.course.id,
                "start": new_start_date,
                "end": new_end_date,
            },
        )
        event = Event.objects.all().first()
        self.assertEquals(event.title, "New TA Session")
        response = self.client.get(
            "/api/occurrences/?course="
            + str(self.course.id)
            + "&filter_start="
            + filter_start
            + "&filter_end="
            + filter_end
        )
        occurrences = json.loads(response.content)
        self.assertEquals(1, len(occurrences))
        self.assertEquals(occurrences[0]["start"], new_start_date)
