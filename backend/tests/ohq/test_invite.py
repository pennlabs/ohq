from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from ohq.invite import parse_and_send_invites
from ohq.models import Course, Membership, MembershipInvite, Semester


User = get_user_model()


class ParseAndSendInvitesTestCase(TestCase):
    def setUp(self):
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
            course_code="000", department="TEST", course_title="Title", semester=self.semester
        )

        self.user1 = User.objects.create(username="user1", email="user1@seas.upenn.edu")
        Membership.objects.create(course=self.course, user=self.user1, kind=Membership.KIND_STUDENT)

        self.user2 = User.objects.create(username="user2", email="user2@seas.upenn.edu")
        Membership.objects.create(course=self.course, user=self.user2, kind=Membership.KIND_TA)

        self.user3 = User.objects.create(username="user3", email="user3@seas.upenn.edu")

        MembershipInvite.objects.create(
            course=self.course, email="user4@wharton.upenn.edu", kind=Membership.KIND_STUDENT
        )

        MembershipInvite.objects.create(
            course=self.course, email="user5@wharton.upenn.edu", kind=Membership.KIND_TA
        )

    def test_invalid_email(self):
        with self.assertRaises(ValidationError):
            parse_and_send_invites(self.course, ["not an email"], Membership.KIND_TA)

    def test_valid_emails(self):
        """
        Test situations where
        * the user is already a member but is different type - user1 (expected: added, not invited)
        * the user is already a member and is same type - user2 (expected: not added, not invited)
        * the user is not a member of the course and has different email - user3 (expected: added, not invited)
        * the email has already been sent an invite but is different type - user4 (expected: not added, invited)
        * the email has already been sent an invite and is same type - user5 (expected: not added, not invited)
        * the user is not a member of any course - user6 (expected: not added, invited)
        """
        members_added, invites_sent = parse_and_send_invites(
            self.course,
            [
                "user1@seas.upenn.edu",
                "user2@seas.upenn.edu",
                "user3@sas.upenn.edu",
                "user4@wharton.upenn.edu",
                "user5@wharton.upenn.edu",
                "user6@nursing.upenn.edu",
            ],
            Membership.KIND_TA,
        )

        # # Correct number of invites and memberships created
        self.assertEqual(2, members_added)
        self.assertEqual(2, invites_sent)

        # Membership is created for user1
        self.assertEqual(
            1,
            Membership.objects.filter(
                user=self.user1, course=self.course, kind=Membership.KIND_TA
            ).count(),
        )

        # Membership is created for user3
        self.assertEqual(
            1,
            Membership.objects.filter(
                user=self.user3, course=self.course, kind=Membership.KIND_TA
            ).count(),
        )

        # Duplicate membership for user2 isn't created
        self.assertEqual(3, Membership.objects.all().count())

        # Invite is sent to user4@wharton.upenn.edu
        self.assertEqual(
            1,
            MembershipInvite.objects.filter(
                email="user4@wharton.upenn.edu", course=self.course, kind=Membership.KIND_TA
            ).count(),
        )

        # Invite is sent to user6@nursing.upenn.edu
        self.assertEqual(
            1,
            MembershipInvite.objects.filter(
                email="user6@nursing.upenn.edu", course=self.course, kind=Membership.KIND_TA
            ).count(),
        )
