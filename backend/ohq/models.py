from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.dispatch import receiver
from email_tools.emails import send_email
from phonenumber_field.modelfields import PhoneNumberField
from schedule.models import Event
from django.urls import reverse
from datetime import timedelta

User = settings.AUTH_USER_MODEL


class Profile(models.Model):
    """
    An extension to a User object that includes additional information.
    """

    # preferred_name = models.CharField(max_length=100)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    sms_notifications_enabled = models.BooleanField(default=False)
    sms_verification_code = models.CharField(max_length=6, blank=True, null=True)
    sms_verification_timestamp = models.DateTimeField(blank=True, null=True)
    sms_verified = models.BooleanField(default=False)
    phone_number = PhoneNumberField(blank=True, null=True)

    SMS_VERIFICATION_EXPIRATION_MINUTES = 10

    def __str__(self):
        return str(self.user)


@receiver(models.signals.post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    Profile.objects.get_or_create(user=instance)
    instance.profile.save()


class Semester(models.Model):
    """
    A semester used to indicate when questions were used.
    Contains a year and season.
    """

    TERM_SPRING = "SPRING"
    TERM_SUMMER = "SUMMER"
    TERM_FALL = "FALL"
    TERM_WINTER = "WINTER"
    TERM_CHOICES = [
        (TERM_SPRING, "Spring"),
        (TERM_SUMMER, "Summer"),
        (TERM_FALL, "Fall"),
        (TERM_WINTER, "Winter"),
    ]
    year = models.IntegerField()
    term = models.CharField(max_length=6, choices=TERM_CHOICES, default=TERM_FALL)

    def term_to_pretty(self):
        return self.term.title()

    def __str__(self):
        return f"{self.term_to_pretty()} {self.year}"


class Course(models.Model):
    """
    A course taught in a specific semester.
    """

    course_code = models.CharField(max_length=10)
    department = models.CharField(max_length=10)
    course_title = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    archived = models.BooleanField(default=False)
    invite_only = models.BooleanField(default=False)
    members = models.ManyToManyField(User, through="Membership", through_fields=("course", "user"))


    # MAX_NUMBER_COURSE_USERS = 1000

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course_code", "department", "semester"], name="unique_course_name"
            )
        ]

    def __str__(self):
        return f"{self.department} {self.course_code}: {str(self.semester)}"


class Membership(models.Model):
    """
    Represents a relationship between a user and a course.
    """

    KIND_STUDENT = "STUDENT"
    KIND_TA = "TA"
    KIND_HEAD_TA = "HEAD_TA"
    KIND_PROFESSOR = "PROFESSOR"
    KIND_CHOICES = [
        (KIND_STUDENT, "Student"),
        (KIND_TA, "TA"),
        (KIND_HEAD_TA, "Head TA"),
        (KIND_PROFESSOR, "Professor"),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    kind = models.CharField(max_length=9, choices=KIND_CHOICES, default=KIND_STUDENT)
    time_created = models.DateTimeField(auto_now_add=True)

    # For staff
    last_active = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["course", "user"], name="unique_membership")]

    @property
    def is_leadership(self):
        return self.kind in [Membership.KIND_PROFESSOR, Membership.KIND_HEAD_TA]

    @property
    def is_ta(self):
        return self.is_leadership or self.kind == Membership.KIND_TA

    def kind_to_pretty(self):
        return [pretty for raw, pretty in self.KIND_CHOICES if raw == self.kind][0]

    def send_email(self):
        """
        Send the email associated with this invitation to the user.
        """

        context = {
            "course": f"{self.course.department} {self.course.course_code}",
            "role": self.kind_to_pretty(),
            "product_link": f"https://{settings.DOMAINS[0]}",
        }
        subject = f"You've been added to {context['course']} OHQ"
        send_email("emails/course_added.html", context, subject, self.user.email)

    def __str__(self):
        return f"<Membership: {self.user} - {self.course} ({self.kind_to_pretty()})>"


class MembershipInvite(models.Model):
    """
    Represents an invitation to a course.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    email = models.EmailField()
    kind = models.CharField(
        max_length=9, choices=Membership.KIND_CHOICES, default=Membership.KIND_STUDENT
    )
    time_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "email"], name="unique_invited_course_user")
        ]

    def kind_to_pretty(self):
        return [pretty for raw, pretty in Membership.KIND_CHOICES if raw == self.kind][0]

    def send_email(self):
        """
        Send the email associated with this invitation to the user.
        """

        context = {
            "course": f"{self.course.department} {self.course.course_code}",
            "role": self.kind_to_pretty(),
            "product_link": f"https://{settings.DOMAINS[0]}",
        }
        subject = f"Invitation to join {context['course']} OHQ"
        send_email("emails/course_invitation.html", context, subject, self.email)

    def __str__(self):
        return f"<MembershipInvite: {self.email} - {self.course} ({self.kind_to_pretty()})>"


class Queue(models.Model):
    """
    A single office hours queue for a class.
    """

    VIDEO_REQUIRED = "REQUIRED"
    VIDEO_OPTIONAL = "OPTIONAL"
    VIDEO_DISABLED = "DISABLED"
    VIDEO_CHOICES = [
        (VIDEO_REQUIRED, "required"),
        (VIDEO_OPTIONAL, "optional"),
        (VIDEO_DISABLED, "disabled"),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField()
    question_template = models.TextField(blank=True, default="")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    archived = models.BooleanField(default=False)
    pin_enabled = models.BooleanField(default=False)
    pin = models.CharField(max_length=50, blank=True, null=True)

    # Estimated wait time for the queue, in minutes
    estimated_wait_time = models.IntegerField(default=-1)
    active = models.BooleanField(default=False)
    # TODO: re-add some sort of scheduling feature?

    # MAX_NUMBER_QUEUES = 2

    # particular user can ask rate_limit_questions in rate_limit_minutes if the queue length is
    # greater than rate_limit_length
    rate_limit_enabled = models.BooleanField(default=False)
    rate_limit_length = models.IntegerField(blank=True, null=True)
    rate_limit_questions = models.IntegerField(blank=True, null=True)
    rate_limit_minutes = models.IntegerField(blank=True, null=True)

    question_timer_enabled = models.BooleanField(default=False)
    question_timer_start_time = models.IntegerField(blank=True, null=True)

    video_chat_setting = models.CharField(
        max_length=8, choices=VIDEO_CHOICES, default=VIDEO_OPTIONAL
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["course", "name"], name="unique_queue_name")]

    def __str__(self):
        return f"{self.course}: {self.name}"


class Tag(models.Model):
    """
    Tags for a course.
    """

    name = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name", "course"], name="unique_course_tag")]

    def __str__(self):
        return f"{self.course}: {self.name}"


class Question(models.Model):
    """
    A question asked within a queue.
    """

    STATUS_ASKED = "ASKED"
    STATUS_WITHDRAWN = "WITHDRAWN"
    STATUS_ACTIVE = "ACTIVE"
    STATUS_REJECTED = "REJECTED"
    STATUS_ANSWERED = "ANSWERED"
    STATUS_CHOICES = [
        (STATUS_ASKED, "Asked"),
        (STATUS_WITHDRAWN, "Withdrawn"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_ANSWERED, "Answered"),
    ]
    text = models.TextField()
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE)
    video_chat_url = models.URLField(blank=True, null=True)

    note = models.CharField(max_length=255, blank=True, null=True)
    resolved_note = models.BooleanField(default=True)

    status = models.CharField(max_length=9, choices=STATUS_CHOICES, default=STATUS_ASKED)

    time_asked = models.DateTimeField(auto_now_add=True)
    asked_by = models.ForeignKey(User, related_name="asked_questions", on_delete=models.CASCADE)

    time_response_started = models.DateTimeField(blank=True, null=True)
    time_responded_to = models.DateTimeField(blank=True, null=True)
    responded_to_by = models.ForeignKey(
        User, related_name="responded_questions", on_delete=models.SET_NULL, blank=True, null=True
    )
    # This field should be a custom message or one of the following:
    # OTHER, NOT_HERE, OH_ENDED, NOT_SPECIFIC, MISSING_TEMPLATE, or WRONG_QUEUE
    rejected_reason = models.CharField(max_length=255, blank=True, null=True)

    should_send_up_soon_notification = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True)
    student_descriptor = models.CharField(max_length=255, blank=True, null=True)


class CourseStatistic(models.Model):
    """
    Most active students/TAs in the past week for a course
    """

    METRIC_STUDENT_QUESTIONS_ASKED = "STUDENT_QUESTIONS_ASKED"
    METRIC_STUDENT_TIME_BEING_HELPED = "STUDENT_TIME_BEING_HELPED"
    METRIC_INSTR_QUESTIONS_ANSWERED = "INSTR_QUESTIONS_ANSWERED"
    METRIC_INSTR_TIME_ANSWERING = "INSTR_TIME_ANSWERING"

    METRIC_CHOICES = [
        (METRIC_STUDENT_QUESTIONS_ASKED, "Student: Questions asked"),
        (METRIC_STUDENT_TIME_BEING_HELPED, "Student: Time being helped"),
        (METRIC_INSTR_QUESTIONS_ANSWERED, "Instructor: Questions answered"),
        (METRIC_INSTR_TIME_ANSWERING, "Instructor: Time answering questions"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    metric = models.CharField(max_length=256, choices=METRIC_CHOICES)
    value = models.DecimalField(max_digits=16, decimal_places=8)
    date = models.DateField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course", "metric", "date"], name="course_statistic"
            )
        ]

    def metric_to_pretty(self):
        return [pretty for raw, pretty in CourseStatistic.METRIC_CHOICES if raw == self.metric][0]

    def __str__(self):
        return f"{self.course}: {self.date}: {self.metric_to_pretty()}"


class QueueStatistic(models.Model):
    """
    Statistics related to a queue
    """

    # add new metrics/statistics
    METRIC_HEATMAP_WAIT = "HEATMAP_AVG_WAIT"
    METRIC_HEATMAP_QUESTIONS_PER_TA = "HEATMAP_QUESTIONS_PER_TA"
    METRIC_AVG_WAIT = "AVG_WAIT"
    METRIC_NUM_ANSWERED = "NUM_ANSWERED"
    METRIC_STUDENTS_HELPED = "STUDENTS_HELPED"
    METRIC_AVG_TIME_HELPING = "AVG_TIME_HELPING"
    METRIC_CHOICES = [
        (METRIC_HEATMAP_WAIT, "Average wait-time heatmap"),
        (METRIC_HEATMAP_QUESTIONS_PER_TA, "Questions per TA heatmap"),
        (METRIC_AVG_WAIT, "Average wait-time per day"),
        (METRIC_NUM_ANSWERED, "Number of questions answered per day"),
        (METRIC_STUDENTS_HELPED, "Students helped per day"),
        (METRIC_AVG_TIME_HELPING, "Average time helping students"),
    ]

    # for specific days during the week - used for heatmap and graphs where day is x-axis
    DAY_SUNDAY = 1
    DAY_MONDAY = 2
    DAY_TUESDAY = 3
    DAY_WEDNESDAY = 4
    DAY_THURSDAY = 5
    DAY_FRIDAY = 6
    DAY_SATURDAY = 7
    DAY_CHOICES = [
        (DAY_SUNDAY, "Sunday"),
        (DAY_MONDAY, "Monday"),
        (DAY_TUESDAY, "Tuesday"),
        (DAY_WEDNESDAY, "Wednesday"),
        (DAY_THURSDAY, "Thursday"),
        (DAY_FRIDAY, "Friday"),
        (DAY_SATURDAY, "Saturday"),
    ]

    queue = models.ForeignKey(Queue, on_delete=models.CASCADE)
    metric = models.CharField(max_length=256, choices=METRIC_CHOICES)
    value = models.DecimalField(max_digits=16, decimal_places=8)

    day = models.IntegerField(choices=DAY_CHOICES, blank=True, null=True)
    hour = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(23)], blank=True, null=True
    )
    date = models.DateField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["queue", "metric", "day", "hour", "date"], name="unique_statistic"
            )
        ]

    def metric_to_pretty(self):
        return [pretty for raw, pretty in QueueStatistic.METRIC_CHOICES if raw == self.metric][0]

    def day_to_pretty(self):
        pretty_lst = [pretty for raw, pretty in QueueStatistic.DAY_CHOICES if raw == self.day]
        if len(pretty_lst):
            return pretty_lst[0]
        else:
            return ""

    def hour_to_pretty(self):
        if self.hour is not None:
            return f"{self.hour}:00 - {self.hour + 1}:00"
        else:
            return ""

    def __str__(self):
        string = f"{self.queue}: {self.metric_to_pretty()}"
        if self.day_to_pretty() != "":
            string += " " + self.day_to_pretty()
        if self.hour_to_pretty() != "":
            string += " " + self.hour_to_pretty()
        return string


class Announcement(models.Model):
    """
    TA announcement within a class
    """

    content = models.TextField()
    author = models.ForeignKey(User, related_name="announcements", on_delete=models.CASCADE)
    time_updated = models.DateTimeField(auto_now=True)
    course = models.ForeignKey(Course, related_name="announcements", on_delete=models.CASCADE)


class UserStatistic(models.Model):
    """
    Statistics related to a user (student or TA) across many courses
    """

    METRIC_TOTAL_QUESTIONS_ASKED = "TOTAL_QUESTIONS_ASKED"
    METRIC_TOTAL_QUESTIONS_ANSWERED = "TOTAL_QUESTIONS_ANSWERED"
    METRIC_TOTAL_TIME_BEING_HELPED = "TOTAL_TIME_BEING_HELPED"
    METRIC_TOTAL_TIME_HELPING = "TOTAL_TIME_HELPING"
    METRIC_TOTAL_STUDENTS_HELPED = "TOTAL_STUDENTS_HELPED"

    METRIC_CHOICES = [
        (METRIC_TOTAL_QUESTIONS_ASKED, "Total questions asked"),
        (METRIC_TOTAL_QUESTIONS_ANSWERED, "Total questions answered"),
        (METRIC_TOTAL_TIME_BEING_HELPED, "Total time being helped"),
        (METRIC_TOTAL_TIME_HELPING, "Total time helping"),
        (METRIC_TOTAL_STUDENTS_HELPED, "Total students helped"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    metric = models.CharField(max_length=256, choices=METRIC_CHOICES)
    value = models.DecimalField(max_digits=16, decimal_places=8)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "metric"], name="unique_user_statistic")
        ]

    def __str__(self):
        return f"{self.user}: {self.metric}"
    
class Occurrence(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, verbose_name=("event"), related_name="occurrences")
    title = models.CharField(("title"), max_length=255, blank=True)
    location = models.CharField(("location"), max_length=255, blank=True)
    description = models.TextField(("description"), blank=True)
    start = models.DateTimeField(("start"), db_index=True)
    end = models.DateTimeField(("end"), db_index=True)
    cancelled = models.BooleanField(("cancelled"), default=False)
    original_start = models.DateTimeField(("original start"))
    original_end = models.DateTimeField(("original end"))
    created_on = models.DateTimeField(("created on"), auto_now_add=True)
    updated_on = models.DateTimeField(("updated on"), auto_now=True)
    interval = models.IntegerField(("interval"), blank=True, validators=[MinValueValidator(5), MaxValueValidator(60)])

    class Meta:
        verbose_name = ("occurrence")
        verbose_name_plural = ("occurrences")
        index_together = (("start", "end"),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = kwargs.get("event", None)
        if not self.title and event:
            self.title = event.title
        if not self.description and event:
            self.description = event.description
        if not self.location and event:
            self.location = event.location

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.pk: # If save is called on object update, not creation
            self.bookings.all().delete()

        delta = self.end - self.start
        delta_minutes = delta.total_seconds() / 60
        booking_count = int(delta_minutes // self.interval)
        for i in range(booking_count):
            booking_start = self.start + timedelta(minutes=i * self.interval)
            booking_end = booking_start + timedelta(minutes=self.interval)
            Booking.objects.create(
                occurrence=self,
                user=None,
                start=booking_start,
                end = booking_end,
            )

    def moved(self):
        return self.original_start != self.start or self.original_end != self.end

    moved = property(moved)

    def move(self, new_start, new_end):
        self.start = new_start
        self.end = new_end
        self.save()

    def cancel(self):
        self.cancelled = True
        self.save()

    def uncancel(self):
        self.cancelled = False
        self.save()

    @property
    def seconds(self):
        return (self.end - self.start).total_seconds()

    @property
    def minutes(self):
        return float(self.seconds) / 60

    @property
    def hours(self):
        return float(self.seconds) / 3600

    def get_absolute_url(self):
        if self.pk is not None:
            return reverse(
                "occurrence",
                kwargs={"occurrence_id": self.pk, "event_id": self.event_id},
            )
        return reverse(
            "occurrence_by_date",
            kwargs={
                "event_id": self.event_id,
                "year": self.start.year,
                "month": self.start.month,
                "day": self.start.day,
                "hour": self.start.hour,
                "minute": self.start.minute,
                "second": self.start.second,
            },
        )

    def get_cancel_url(self):
        if self.pk is not None:
            return reverse(
                "cancel_occurrence",
                kwargs={"occurrence_id": self.pk, "event_id": self.event_id},
            )
        return reverse(
            "cancel_occurrence_by_date",
            kwargs={
                "event_id": self.event_id,
                "year": self.start.year,
                "month": self.start.month,
                "day": self.start.day,
                "hour": self.start.hour,
                "minute": self.start.minute,
                "second": self.start.second,
            },
        )

    def get_edit_url(self):
        if self.pk is not None:
            return reverse(
                "edit_occurrence",
                kwargs={"occurrence_id": self.pk, "event_id": self.event_id},
            )
        return reverse(
            "edit_occurrence_by_date",
            kwargs={
                "event_id": self.event_id,
                "year": self.start.year,
                "month": self.start.month,
                "day": self.start.day,
                "hour": self.start.hour,
                "minute": self.start.minute,
                "second": self.start.second,
            },
        )

    def __str__(self):
        start_str = self.start.strftime("%Y-%m-%d %H:%M:%S")
        end_str = self.end.strftime("%Y-%m-%d %H:%M:%S")
        return f"{start_str} to {end_str}"

    def __lt__(self, other):
        return self.end < other.end

    def __hash__(self):
        if not self.pk:
            raise TypeError("Model instances without primary key value are unhashable")
        return hash(self.pk)

    def __eq__(self, other):
        return (
            isinstance(other, Occurrence)
            and self.original_start == other.original_start
            and self.original_end == other.original_end
        )

class Booking(models.Model):
    """
    Booking within an occurrence
    """

    occurrence = models.ForeignKey(Occurrence, on_delete=models.CASCADE, related_name="bookings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    start = models.DateTimeField("start", db_index=True)
    end = models.DateTimeField("end", db_index=True)

    class Meta:
        verbose_name = ("booking")
        verbose_name_plural = ("bookings")
        ordering = ["start"]
        index_together = (("start", "end"),)

    def __str__(self):
        start_str = self.start.strftime("%Y-%m-%d %H:%M:%S")
        end_str = self.end.strftime("%Y-%m-%d %H:%M:%S")
        return f"{start_str} to {end_str}"