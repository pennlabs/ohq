from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from schedule.models import Calendar, Event, EventRelationManager

from ohq.models import (
    Course,
    CourseStatistic,
    Membership,
    MembershipInvite,
    Question,
    Queue,
    QueueStatistic,
    Semester,
    Tag,
    Occurrence,
)


User = get_user_model()


class ProfileTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user")

    def test_str(self):
        self.assertEqual(str(self.user.profile), str(self.user))


class TagTestCase(TestCase):
    def setUp(self):
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
            course_code="000", department="TEST", course_title="Title", semester=self.semester
        )
        self.tag = Tag.objects.create(name="Test Tag", course=self.course)

    def test_str(self):
        self.assertEqual(str(self.tag), f"{self.course}: Test Tag")


class CourseTestCase(TestCase):
    def setUp(self):
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
            course_code="000", department="TEST", course_title="Title", semester=self.semester
        )

    def test_str(self):
        self.assertEqual(
            str(self.course),
            f"{self.course.department} {self.course.course_code}: {self.course.semester}",
        )


class MembershipTestCase(TestCase):
    def setUp(self):
        semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        course = Course.objects.create(
            course_code="000", department="TEST", course_title="Title", semester=semester
        )
        self.user = User.objects.create(username="user", email="example@example.com")
        self.membership = Membership.objects.create(
            course=course, user=self.user, kind=Membership.KIND_PROFESSOR
        )

    def test_kind_to_pretty(self):
        self.assertEqual(self.membership.kind_to_pretty(), "Professor")

    def test_is_leadership(self):
        self.assertTrue(self.membership.is_leadership)

    def test_is_ta(self):
        self.assertTrue(self.membership.is_ta)

    def test_str(self):
        mem = self.membership
        self.assertEqual(
            str(mem), f"<Membership: {mem.user} - {mem.course} ({mem.kind_to_pretty()})>"
        )

    def test_send_email(self):
        self.membership.send_email()
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual(self.user.email, email.to[0])


class MembershipInviteTestCase(TestCase):
    def setUp(self):
        semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        course = Course.objects.create(
            course_code="000", department="TEST", course_title="Title", semester=semester
        )
        self.invite = MembershipInvite.objects.create(
            course=course, email="me@example.com", kind=Membership.KIND_PROFESSOR
        )

    def test_kind_to_pretty(self):
        self.assertEqual(self.invite.kind_to_pretty(), "Professor")

    def test_str(self):
        inv = self.invite
        self.assertEqual(
            str(inv), f"<MembershipInvite: {inv.email} - {inv.course} ({inv.kind_to_pretty()})>"
        )

    def test_send_email(self):
        self.invite.send_email()
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual(self.invite.email, email.to[0])


class QueueTestCase(TestCase):
    def setUp(self):
        semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        course = Course.objects.create(
            course_code="000", department="TEST", course_title="Title", semester=semester
        )
        self.queue = Queue.objects.create(name="Queue", course=course)

    def test_str(self):
        self.assertEqual(str(self.queue), f"{self.queue.course}: {self.queue.name}")


class QuestionTestCase(TestCase):
    def setUp(self):
        semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        course = Course.objects.create(
            course_code="000", department="TEST", course_title="Title", semester=semester
        )
        queue = Queue.objects.create(name="Queue", course=course)
        user = User.objects.create(username="user", email="example@example.com")
        self.question = Question.objects.create(text="Question?", queue=queue, asked_by=user)

    def test_str(self):
        # TODO: write this
        pass


class SemesterTestCase(TestCase):
    def setUp(self):
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)

    def test_term_to_pretty(self):
        self.assertEqual(self.semester.term_to_pretty(), self.semester.term.title())

    def test_str(self):
        self.assertEqual(str(self.semester), f"{self.semester.term.title()} {self.semester.year}")


class CourseStatisticTestCase(TestCase):
    def setUp(self):
        semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
            course_code="000", department="TEST", course_title="Title", semester=semester
        )
        self.user = User.objects.create_user("user", "user@a.com", "user")
        today = timezone.datetime.today().date()

        self.student_num_questions_asked = CourseStatistic.objects.create(
            course=self.course,
            user=self.user,
            metric=CourseStatistic.METRIC_STUDENT_QUESTIONS_ASKED,
            value=100.00,
            date=today,
        )

        self.student_time_being_helped = CourseStatistic.objects.create(
            course=self.course,
            user=self.user,
            metric=CourseStatistic.METRIC_STUDENT_TIME_BEING_HELPED,
            value=100.00,
            date=today,
        )

        self.instructor_num_questions_answered = CourseStatistic.objects.create(
            course=self.course,
            user=self.user,
            metric=CourseStatistic.METRIC_INSTR_QUESTIONS_ANSWERED,
            value=100.00,
            date=today,
        )

        self.instructor_time_answering_questions = CourseStatistic.objects.create(
            course=self.course,
            user=self.user,
            metric=CourseStatistic.METRIC_INSTR_TIME_ANSWERING,
            value=100.00,
            date=today,
        )

    def test_metric_to_pretty(self):

        self.assertEqual(
            self.student_num_questions_asked.metric_to_pretty(), "Student: Questions asked"
        )

        self.assertEqual(
            self.student_time_being_helped.metric_to_pretty(),
            "Student: Time being helped",
        )

        self.assertEqual(
            self.instructor_num_questions_answered.metric_to_pretty(),
            "Instructor: Questions answered",
        )

        self.assertEqual(
            self.instructor_time_answering_questions.metric_to_pretty(),
            "Instructor: Time answering questions",
        )

    def test_str(self):

        today = timezone.datetime.today().date()
        self.assertEqual(
            str(self.student_num_questions_asked),
            f"{self.course}: {today}: Student: Questions asked",
        )

        self.assertEqual(
            str(self.student_time_being_helped),
            f"{self.course}: {today}: Student: Time being helped",
        )

        self.assertEqual(
            str(self.instructor_num_questions_answered),
            f"{self.course}: {today}: Instructor: Questions answered",
        )

        self.assertEqual(
            str(self.instructor_time_answering_questions),
            f"{self.course}: {today}: Instructor: Time answering questions",
        )


class QueueStatisticTestCase(TestCase):
    def setUp(self):
        semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        course = Course.objects.create(
            course_code="000", department="TEST", course_title="Title", semester=semester
        )
        self.queue = Queue.objects.create(name="Queue", course=course)

        self.heatmap_queue_statistic = QueueStatistic.objects.create(
            queue=self.queue,
            metric=QueueStatistic.METRIC_HEATMAP_WAIT,
            value=100.00,
            day=QueueStatistic.DAY_MONDAY,
            hour=0,
        )
        today = timezone.datetime.today().date()

        self.avg_wait_time_queue_statistic = QueueStatistic.objects.create(
            queue=self.queue,
            metric=QueueStatistic.METRIC_AVG_WAIT,
            value=150.00,
            date=today - timezone.timedelta(days=1),
        )

        self.num_questions_answered_queue_statistic = QueueStatistic.objects.create(
            queue=self.queue,
            metric=QueueStatistic.METRIC_NUM_ANSWERED,
            value=10.00,
            date=today - timezone.timedelta(days=1),
        )

        self.num_students_helped_queue_statistic = QueueStatistic.objects.create(
            queue=self.queue,
            metric=QueueStatistic.METRIC_STUDENTS_HELPED,
            value=50.00,
            date=today - timezone.timedelta(days=1),
        )

        self.avg_time_helping_queue_statistic = QueueStatistic.objects.create(
            queue=self.queue,
            metric=QueueStatistic.METRIC_AVG_TIME_HELPING,
            value=120.00,
            date=today - timezone.timedelta(days=1),
        )

    def test_str(self):
        self.assertEqual(
            str(self.heatmap_queue_statistic),
            f"{self.queue}: {self.heatmap_queue_statistic.get_metric_display()} "
            f"{self.heatmap_queue_statistic.get_day_display()} "
            f"{self.heatmap_queue_statistic.hour}:00 - {self.heatmap_queue_statistic.hour+1}:00",
        )

        self.assertEqual(
            str(self.avg_wait_time_queue_statistic),
            f"{self.queue}: {self.avg_wait_time_queue_statistic.get_metric_display()}",
        )

        self.assertEqual(
            str(self.num_questions_answered_queue_statistic),
            f"{self.queue}: {self.num_questions_answered_queue_statistic.get_metric_display()}",
        )

        self.assertEqual(
            str(self.num_students_helped_queue_statistic),
            f"{self.queue}: {self.num_students_helped_queue_statistic.get_metric_display()}",
        )

        self.assertEqual(
            str(self.avg_time_helping_queue_statistic),
            f"{self.queue}: {self.avg_time_helping_queue_statistic.get_metric_display()}",
        )

class OccurrenceTestCase(TestCase):
    def setUp(self):
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
        course_code="000", department="Penn Labs", semester=self.semester
    )
        self.start_time = datetime.strptime("2021-12-05T12:41:37Z", "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        self.end_time = datetime.strptime("2021-12-06T12:41:37Z", "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        self.default_calendar = Calendar.objects.create(name="DefaultCalendar")
        self.event = Event.objects.create(
            title="Event",
            calendar=self.default_calendar,
            rule=None,
            start=self.start_time,
            end=self.end_time,
        )
        erm = EventRelationManager()
        erm.create_relation(event=self.event, content_object=self.course)
        
        self.occurrence = Occurrence.objects.create(
            event=self.event,
            start=self.start_time,
            end=self.end_time,
            original_start=self.start_time,
            original_end=self.end_time,
            interval=10,
        )
        self.occurrence.save()

        self.bookings = self.occurrence.bookings.all()

    
    def test_occurrence_creates_bookings(self):
        delta = self.end_time - self.start_time
        delta_minutes = delta.total_seconds() / 60
        booking_count = int(delta_minutes // self.occurrence.interval)
        self.assertEqual(len(self.bookings), booking_count)

    def test_occurrence_update_recreates_bookings(self):
        old_bookings_count = len(self.bookings)
        old_first_booking = self.occurrence.bookings.first()
        old_last_booking = self.occurrence.bookings.last()

        self.occurrence.start += timedelta(minutes=10)
        self.occurrence.end += timedelta(minutes=30)
        self.occurrence.save()
        
        new_bookings = self.occurrence.bookings.all()
        new_first_booking = new_bookings.first()
        new_last_booking = new_bookings.last()

        self.assertNotEqual(old_bookings_count, len(new_bookings))
        self.assertNotEqual(old_first_booking.start, new_first_booking.start)
        self.assertNotEqual(old_last_booking.end, new_last_booking.end)
