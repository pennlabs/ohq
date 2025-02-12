from datetime import datetime
from unittest.mock import patch

import pytz
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from parameterized import parameterized
from rest_framework.test import APIClient
from schedule.models import Calendar, Event, EventRelationManager

from ohq.models import (
    Announcement,
    Course,
    Membership,
    MembershipInvite,
    Question,
    Queue,
    Semester,
    Tag,
    Occurrence,
)


User = get_user_model()

users = ["professor", "head_ta", "ta", "student", "non_member", "anonymous"]


def get_test_name(testcase_func, _, param):
    """
    A function to create test names for parameterized
    For example, a test case named test_list will generate names
    of the form test_list_professor, test_list_head_ta, etc.
    """

    return f"{testcase_func.__name__}_{param.args[0]}"


def setUp(self):
    """
    General set up used in each test case.
    """

    self.client = APIClient()
    self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
    self.course = Course.objects.create(
        course_code="000", department="Penn Labs", semester=self.semester
    )

    # Create users
    self.professor = User.objects.create(username="professor")
    self.head_ta = User.objects.create(username="head_ta")
    self.ta = User.objects.create(username="ta")
    self.student = User.objects.create(username="student")
    self.non_member = User.objects.create(username="non_member")
    self.anonymous = None

    # Create Memberships
    Membership.objects.create(
        course=self.course, user=self.professor, kind=Membership.KIND_PROFESSOR
    )
    Membership.objects.create(course=self.course, user=self.head_ta, kind=Membership.KIND_HEAD_TA)
    Membership.objects.create(course=self.course, user=self.ta, kind=Membership.KIND_TA)
    Membership.objects.create(course=self.course, user=self.student, kind=Membership.KIND_STUDENT)


def test(self, user, action_name, request, url, data=None):
    """
    A helper function to reduce the duplicated code in each test case
    """

    self.client.force_authenticate(user=getattr(self, user))
    response = getattr(self.client, request)(url, data)
    self.client.force_authenticate(user=None)
    self.assertEqual(self.expected[action_name][user], response.status_code)


class CourseTestCase(TestCase):
    def setUp(self):
        setUp(self)

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 200,
                "anonymous": 403,
            },
            "create": {
                "professor": 201,
                "head_ta": 201,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "retrieve": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 200,
                "anonymous": 403,
            },
            "destroy": {
                "professor": 403,
                "head_ta": 403,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify": {
                "professor": 200,
                "head_ta": 200,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify-archived": {
                "professor": 403,
                "head_ta": 403,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(self, user, "list", "get", reverse("ohq:course-list"))

    @parameterized.expand(users, name_func=get_test_name)
    def test_create(self, user):
        test(
            self,
            user,
            "create",
            "post",
            reverse("ohq:course-list"),
            {
                "course_code": "000",
                "department": "TEST",
                "course_title": "Course",
                "semester": self.semester.id,
                "created_role": user.upper(),
            },
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_retrieve(self, user):
        test(self, user, "retrieve", "get", reverse("ohq:course-detail", args=[self.course.id]))

    @parameterized.expand(users, name_func=get_test_name)
    def test_destroy(self, user):
        test(self, user, "destroy", "delete", reverse("ohq:course-detail", args=[self.course.id]))

    @parameterized.expand(users, name_func=get_test_name)
    def test_modify(self, user):
        test(
            self,
            user,
            "modify",
            "patch",
            reverse("ohq:course-detail", args=[self.course.id]),
            {"description": "new"},
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_modify_archived(self, user):
        """
        Ensure no one can modify an archived course.
        """

        self.course.archived = True
        self.course.save()
        test(
            self,
            user,
            "modify-archived",
            "patch",
            reverse("ohq:course-detail", args=[self.course.id]),
            {"description": "new"},
        )


class QueueTestCase(TestCase):
    def setUp(self):
        setUp(self)
        self.queue = Queue.objects.create(name="Queue", course=self.course)

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "create": {
                "professor": 201,
                "head_ta": 201,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "retrieve": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "destroy": {
                "professor": 204,
                "head_ta": 204,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "clear": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(self, user, "list", "get", reverse("ohq:queue-list", args=[self.course.id]))

    @parameterized.expand(users, name_func=get_test_name)
    def test_create(self, user):
        test(
            self,
            user,
            "create",
            "post",
            reverse("ohq:queue-list", args=[self.course.id]),
            {"name": "new", "description": "description"},
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_retrieve(self, user):
        test(
            self,
            user,
            "retrieve",
            "get",
            reverse("ohq:queue-detail", args=[self.course.id, self.queue.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_destroy(self, user):
        test(
            self,
            user,
            "destroy",
            "delete",
            reverse("ohq:queue-detail", args=[self.course.id, self.queue.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_modify(self, user):
        test(
            self,
            user,
            "modify",
            "patch",
            reverse("ohq:queue-detail", args=[self.course.id, self.queue.id]),
            {"active": True},
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_clear(self, user):
        """
        Test who can clear questions from a queue.
        """

        test(
            self,
            user,
            "clear",
            "post",
            reverse("ohq:queue-clear", args=[self.course.id, self.queue.id]),
        )


class TagTestCase(TestCase):
    def setUp(self):
        setUp(self)
        self.tag = Tag.objects.create(name="test", course=self.course)

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "create": {
                "professor": 201,
                "head_ta": 201,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "retrieve": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "destroy": {
                "professor": 204,
                "head_ta": 204,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify": {
                "professor": 200,
                "head_ta": 200,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(self, user, "list", "get", reverse("ohq:tag-list", args=[self.course.id]))

    @parameterized.expand(users, name_func=get_test_name)
    def test_create(self, user):
        test(
            self,
            user,
            "create",
            "post",
            reverse("ohq:tag-list", args=[self.course.id]),
            {"name": "new", "description": "description"},
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_retrieve(self, user):
        test(
            self,
            user,
            "retrieve",
            "get",
            reverse("ohq:tag-detail", args=[self.course.id, self.tag.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_destroy(self, user):
        test(
            self,
            user,
            "destroy",
            "delete",
            reverse("ohq:tag-detail", args=[self.course.id, self.tag.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_modify(self, user):
        test(
            self,
            user,
            "modify",
            "patch",
            reverse("ohq:tag-detail", args=[self.course.id, self.tag.id]),
            {"name": "test2"},
        )


class QuestionTestCase(TestCase):
    def setUp(self):
        setUp(self)
        self.queue = Queue.objects.create(name="Queue", course=self.course)
        self.rate_limit_queue = Queue.objects.create(
            name="Rate Limit Queue",
            course=self.course,
            rate_limit_enabled=True,
            rate_limit_length=2,
            rate_limit_minutes=10,
            rate_limit_questions=2,
        )
        self.question = Question.objects.create(queue=self.queue, asked_by=self.student)
        self.other_question = Question.objects.create(queue=self.queue, asked_by=self.ta)
        self.tag = Tag.objects.create(name="existing-tag", course=self.course)

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "last": {
                "professor": 403,
                "head_ta": 403,
                "ta": 403,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "quota-count": {
                "professor": 403,
                "head_ta": 403,
                "ta": 403,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "create": {
                "professor": 403,
                "head_ta": 403,
                "ta": 403,
                "student": 201,
                "non_member": 403,
                "anonymous": 403,
            },
            "create-existing": {"student": 403},
            "create-tag-existing": {"student": 201},
            "create-tag-new": {"student": 201},
            "retrieve": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "position": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "retrieve-other": {"student": 404},
            "position-other": {"student": 404},
            "destroy": {
                "professor": 403,
                "head_ta": 403,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify-tag-existing": {"student": 200},
            "modify-tag-new": {"student": 200},
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(
            self,
            user,
            "list",
            "get",
            reverse("ohq:question-list", args=[self.course.id, self.queue.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_last(self, user):
        test(
            self,
            user,
            "last",
            "get",
            reverse("ohq:question-last", args=[self.course.id, self.queue.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_quota_count(self, user):
        test(
            self,
            user,
            "quota-count",
            "get",
            reverse("ohq:question-quota-count", args=[self.course.id, self.rate_limit_queue.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_create(self, user):
        self.question.status = Question.STATUS_ANSWERED
        self.question.save()
        test(
            self,
            user,
            "create",
            "post",
            reverse("ohq:question-list", args=[self.course.id, self.queue.id]),
            {"text": "question", "tags": []},
        )

    def test_create_student_existing(self):
        """
        Ensure a student can't submit multiple questions to a queue.
        """

        test(
            self,
            "student",
            "create-existing",
            "post",
            reverse("ohq:question-list", args=[self.course.id, self.queue.id]),
            {"text": "question"},
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_retrieve(self, user):
        test(
            self,
            user,
            "retrieve",
            "get",
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
        )

    def test_retrieve_student_other_question(self):
        """
        Ensure a student can't access see anyone else's questions.
        """

        test(
            self,
            "student",
            "retrieve-other",
            "get",
            reverse(
                "ohq:question-detail", args=[self.course.id, self.queue.id, self.other_question.id]
            ),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_position(self, user):
        test(
            self,
            user,
            "position",
            "get",
            reverse(
                "ohq:question-position", args=[self.course.id, self.queue.id, self.question.id]
            ),
        )

    def test_position_student_other_question(self):
        """
        Ensure a student can't access see anyone else's question position.
        """

        test(
            self,
            "student",
            "position-other",
            "get",
            reverse(
                "ohq:question-position",
                args=[self.course.id, self.queue.id, self.other_question.id],
            ),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_destroy(self, user):
        test(
            self,
            user,
            "destroy",
            "delete",
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    @patch("ohq.serializers.sendUpNextNotificationTask.delay")
    def test_modify(self, user, mock_delay):
        status = Question.STATUS_WITHDRAWN if user == "student" else Question.STATUS_ACTIVE
        test(
            self,
            user,
            "modify",
            "patch",
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"status": status},
        )
        if user == "student":
            mock_delay.assert_called()
        else:
            mock_delay.assert_not_called()

    def test_create_existing_tag(self):
        """
        Ensure a student can create a question with existing tags.
        """
        self.question.delete()
        test(
            self,
            "student",
            "create-tag-existing",
            "post",
            reverse("ohq:question-list", args=[self.course.id, self.queue.id]),
            {"text": "question", "tags": [{"name": "existing-tag"}]},
        )

    def test_create_new_tag(self):
        """
        Ensure a student can not create a question with new tags.
        """

        self.question.delete()
        test(
            self,
            "student",
            "create-tag-new",
            "post",
            reverse("ohq:question-list", args=[self.course.id, self.queue.id]),
            {"text": "question", "tags": [{"name": "new-tag"}]},
        )
        question = Question.objects.get(text="question")
        self.assertEqual(0, question.tags.all().count())
        self.assertEqual(1, Tag.objects.all().count())

    def test_update_existing_tag(self):
        """
        Ensure a student can update a question with existing tags.
        """

        test(
            self,
            "student",
            "modify-tag-existing",
            "patch",
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"tags": [{"name": "existing-tag"}]},
        )

    def test_update_new_tag(self):
        """
        Ensure a student can not update a question with existing tags.
        """

        test(
            self,
            "student",
            "modify-tag-new",
            "patch",
            reverse("ohq:question-detail", args=[self.course.id, self.queue.id, self.question.id]),
            {"tags": [{"name": "new-tag"}]},
        )


class QuestionSearchTestCase(TestCase):
    def setUp(self):
        setUp(self)
        self.queue = Queue.objects.create(name="Queue", course=self.course)
        self.question = Question.objects.create(queue=self.queue, asked_by=self.student)

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(
            self,
            user,
            "list",
            "get",
            reverse("ohq:questionsearch", args=[self.course.id]),
        )


class MembershipTestCase(TestCase):
    def setUp(self):
        setUp(self)
        self.membership = Membership.objects.get(course=self.course, user=self.professor)

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "create-open": {
                "professor": 403,
                "head_ta": 403,
                "ta": 403,
                "student": 403,
                "non_member": 201,
                "anonymous": 403,
            },
            "create-invite-only": {
                "professor": 403,
                "head_ta": 403,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "retrieve": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "destroy": {
                "professor": 204,
                "head_ta": 204,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify": {
                "professor": 200,
                "head_ta": 200,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(self, user, "list", "get", reverse("ohq:member-list", args=[self.course.id]))

    @parameterized.expand(users, name_func=get_test_name)
    def test_create_open(self, user):
        test(
            self,
            user,
            "create-open",
            "post",
            reverse("ohq:member-list", args=[self.course.id]),
            {},
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_create_invite_only(self, user):
        self.course.invite_only = True
        self.course.save()
        test(
            self,
            user,
            "create-invite-only",
            "post",
            reverse("ohq:member-list", args=[self.course.id]),
            {},
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_retrieve(self, user):
        test(
            self,
            user,
            "retrieve",
            "get",
            reverse("ohq:member-detail", args=[self.course.id, self.membership.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_destroy(self, user):
        test(
            self,
            user,
            "destroy",
            "delete",
            reverse("ohq:member-detail", args=[self.course.id, self.membership.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_modify(self, user):
        test(
            self,
            user,
            "modify",
            "patch",
            reverse("ohq:member-detail", args=[self.course.id, self.membership.id]),
            {"description": "new"},
        )


class MembershipInviteTestCase(TestCase):
    def setUp(self):
        setUp(self)
        self.invite = MembershipInvite.objects.create(course=self.course, email="me@example.com")

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "create": {
                "professor": 201,
                "head_ta": 201,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "retrieve": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "destroy": {
                "professor": 204,
                "head_ta": 204,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify": {
                "professor": 200,
                "head_ta": 200,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(self, user, "list", "get", reverse("ohq:invite-list", args=[self.course.id]))

    @parameterized.expand(users, name_func=get_test_name)
    def test_create(self, user):
        test(
            self,
            user,
            "create",
            "post",
            reverse("ohq:invite-list", args=[self.course.id]),
            {"email": "test@example.com", "kind": Membership.KIND_STUDENT},
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_retrieve(self, user):
        test(
            self,
            user,
            "retrieve",
            "get",
            reverse("ohq:invite-detail", args=[self.course.id, self.invite.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_destroy(self, user):
        test(
            self,
            user,
            "destroy",
            "delete",
            reverse("ohq:invite-detail", args=[self.course.id, self.invite.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_modify(self, user):
        test(
            self,
            user,
            "modify",
            "patch",
            reverse("ohq:invite-detail", args=[self.course.id, self.invite.id]),
            {"description": "new"},
        )


class MassInviteTestCase(TestCase):
    def setUp(self):
        setUp(self)

        # Expected results
        self.expected = {
            "create": {
                "professor": 201,
                "head_ta": 201,
                "ta": 403,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            }
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_create(self, user):
        test(
            self,
            user,
            "create",
            "post",
            reverse("ohq:mass-invite", args=[self.course.id]),
            {"emails": "test@example.com,test2@example.com", "kind": Membership.KIND_STUDENT},
        )


class CourseStatisticTestCase(TestCase):
    def setUp(self):
        setUp(self)

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(
            self,
            user,
            "list",
            "get",
            reverse("ohq:course-statistic", args=[self.course.id]),
        )


class QueueStatisticTestCase(TestCase):
    def setUp(self):
        setUp(self)
        self.queue = Queue.objects.create(name="Queue", course=self.course)

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(
            self,
            user,
            "list",
            "get",
            reverse("ohq:queue-statistic", args=[self.course.id, self.queue.id]),
        )


class AnnouncementTestCase(TestCase):
    def setUp(self):
        setUp(self)
        self.announcement = Announcement.objects.create(
            course=self.course, author=self.professor, content="Original announcement"
        )

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "create": {
                "professor": 201,
                "head_ta": 201,
                "ta": 201,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "retrieve": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "destroy": {
                "professor": 204,
                "head_ta": 204,
                "ta": 204,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(self, user, "list", "get", reverse("ohq:announcement-list", args=[self.course.id]))

    @parameterized.expand(users, name_func=get_test_name)
    def test_create(self, user):
        content = "New announcement"
        test(
            self,
            user,
            "create",
            "post",
            reverse("ohq:announcement-list", args=[self.course.id]),
            {"content": content},
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_retrieve(self, user):
        test(
            self,
            user,
            "retrieve",
            "get",
            reverse("ohq:announcement-detail", args=[self.course.id, self.announcement.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_destroy(self, user):
        test(
            self,
            user,
            "destroy",
            "delete",
            reverse("ohq:announcement-detail", args=[self.course.id, self.announcement.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_modify(self, user):
        test(
            self,
            user,
            "modify",
            "patch",
            reverse("ohq:announcement-detail", args=[self.course.id, self.announcement.id]),
            {"content": "Updated announcement"},
        )


class EventTestCase(TestCase):
    def setUp(self):
        setUp(self)
        self.default_calendar = Calendar.objects.create(name="DefaultCalendar")
        self.event = Event.objects.create(
            title="Event",
            calendar=self.default_calendar,
            rule=None,
            start=datetime.now(tz=pytz.utc),
            end=datetime.now(tz=pytz.utc),
        )
        erm = EventRelationManager()
        erm.create_relation(event=self.event, content_object=self.course)

        self.start_time = "2019-08-24T14:15:22Z"
        self.end_time = "2019-09-24T14:15:22Z"
        self.title = "TA Session"
        self.new_title = "New TA Session"

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "create": {
                "professor": 201,
                "head_ta": 201,
                "ta": 201,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "retrieve": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "destroy": {
                "professor": 204,
                "head_ta": 204,
                "ta": 204,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(self, user, "list", "get", "/api/events/?course=" + str(self.course.id))

    @parameterized.expand(users, name_func=get_test_name)
    def test_create(self, user):
        test(
            self,
            user,
            "create",
            "post",
            reverse("ohq:event-list"),
            {
                "start": self.start_time,
                "end": self.end_time,
                "title": self.title,
                "rule": {"frequency": "WEEKLY"},
                "endRecurringPeriod": self.end_time,
                "courseId": self.course.id,
            },
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_retrieve(self, user):
        test(
            self,
            user,
            "retrieve",
            "get",
            reverse("ohq:event-detail", args=[self.event.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_destroy(self, user):
        test(self, user, "destroy", "delete", reverse("ohq:event-detail", args=[self.event.id]))

    @parameterized.expand(users, name_func=get_test_name)
    def test_modify(self, user):
        test(
            self,
            user,
            "modify",
            "patch",
            reverse("ohq:event-detail", args=[self.event.id]),
            {"title": self.new_title, "courseId": self.course.id},
        )


class OccurrenceTestCase(TestCase):
    def setUp(self):
        setUp(self)

        self.start_time = datetime.strptime("2021-12-05T12:41:37Z", "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=pytz.utc
        )
        self.end_time = datetime.strptime("2021-12-06T12:41:37Z", "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=pytz.utc
        )
        self.title = "TA Session"
        self.new_title = "New TA Session"
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

        self.filter_start = "2021-12-05T12:40:37Z"
        self.filter_end = "2021-12-12T12:42:37Z"

        self.occurrence = self.event.get_occurrences(
            datetime.strptime(self.filter_start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc),
            datetime.strptime(self.filter_end, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc),
        )[0]
        self.occurrence.save()

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "retrieve": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 403,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(
            self,
            user,
            "list",
            "get",
            "/api/occurrences/?course="
            + str(self.course.id)
            + "&filter_start="
            + self.filter_start
            + "&filter_end="
            + self.filter_end,
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_retrieve(self, user):
        test(
            self,
            user,
            "retrieve",
            "get",
            reverse("ohq:occurrence-detail", args=[self.occurrence.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_modify(self, user):
        test(
            self,
            user,
            "modify",
            "patch",
            reverse("ohq:occurrence-detail", args=[self.occurrence.id]),
            {"title": self.new_title, "courseId": self.course.id},
        )

class BookingTestCase(TestCase):
    def setUp(self):
        setUp(self)

        self.start_time = datetime.strptime("2021-12-05T12:41:37Z", "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=pytz.utc
        )
        self.end_time = datetime.strptime("2021-12-06T12:41:37Z", "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=pytz.utc
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

        self.booking = self.occurrence.bookings.first()

        # Expected results
        self.expected = {
            "list": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "retrieve": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
            "modify": {
                "professor": 200,
                "head_ta": 200,
                "ta": 200,
                "student": 200,
                "non_member": 403,
                "anonymous": 403,
            },
        }

    @parameterized.expand(users, name_func=get_test_name)
    def test_list(self, user):
        test(
            self,
            user,
            "list",
            "get",
            reverse("ohq:booking-list") + f"?occurrence={self.occurrence.id}",
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_retrieve(self, user):
        test(
            self,
            user,
            "retrieve",
            "get",
            reverse("ohq:booking-detail", args=[self.booking.id]),
        )

    @parameterized.expand(users, name_func=get_test_name)
    def test_modify(self, user):
        test(
            self,
            user,
            "modify",
            "patch",
            reverse("ohq:booking-detail", args=[self.booking.id]),
            {"user": self.student.id},
        )