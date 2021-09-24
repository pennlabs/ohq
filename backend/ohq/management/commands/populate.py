import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ohq.models import Course, Membership, MembershipInvite, Profile, Question, Queue, Semester


now = timezone.now()

# creating data for 6 courses, 8 queues, 10 questions
courses = [
    {
        "course_code": "199",
        "department": "CIS",
        "course_title": "Kevin's Kevin",
        "description": "Examining the wonders of Kevin.",
        "queues": [
            {
                "name": "Kevin-related Questions",
                "description": "Have a question about Kevin? Ask here!",
                "archived": False,
                "estimated_wait_time": 100,
                "active": True,
                "questions": [
                    {
                        "text": "How many joints does Kevin's leg have?",
                        "video_chat_url": "https://upenn.zoom.us/j/jfawdjf308220740182aldskjf",
                        "status": Question.STATUS_ACTIVE,
                        "time_asked": now - datetime.timedelta(minutes=48),
                        "time_response_started": now - datetime.timedelta(minutes=30),
                        "should_send_up_soon_notification": True,
                    },
                ],
                "video_chat_setting": Queue.VIDEO_REQUIRED,
            },
        ],
        "semester": {"year": 2020, "term": Semester.TERM_FALL},
        "archived": False,
        "invite_only": False,
    },
    {
        "course_code": "101",
        "department": "OIDD",
        "course_title": "Code Coverage",
        "description": "Professor Davis shows the entire Penn Labs team how to code coverage :)",
        "queues": [
            {
                "name": "Questions that Armaan has for Davis",
                "description": "Code Coverage is important!",
                "archived": False,
                "estimated_wait_time": 1,
                "active": True,
                "questions": [
                    {
                        "text": "How do I code coverage, almight Davis?",
                        "video_chat_url": "https://upenn.zoom.us/j/adkjfaqiowdskjf",
                        "status": Question.STATUS_REJECTED,
                        "time_asked": now - datetime.timedelta(minutes=121),
                        "time_response_started": now - datetime.timedelta(minutes=12),
                        "time_responded_to": now - datetime.timedelta(minutes=12),
                        "rejected_reason": "NOT_SPECIFIC",
                        "should_send_up_soon_notification": False,
                    },
                ],
                "video_chat_setting": Queue.VIDEO_REQUIRED,
            },
        ],
        "semester": {"year": 2020, "term": Semester.TERM_SUMMER},
        "archived": False,
        "invite_only": False,
    },
    {
        "course_code": "200",
        "department": "ART",
        "course_title": "The Crayola Perspective",
        "description": "Crayons! Markers! Learn to use these technical tools and gain new skills!",
        "queues": [],
        "semester": {"year": 2020, "term": Semester.TERM_FALL},
        "archived": False,
        "invite_only": True,
    },
    {
        "course_code": "700",
        "department": "WH",
        "course_title": "Snake City",
        "description": "Free internships at Goldman Sachs. We've got Morgan Stanley too.",
        "queues": [
            {
                "name": "Goldman Sachs Questions",
                "description": "Free as in easy to get into? Or free as in I don't get paid?",
                "archived": False,
                "estimated_wait_time": 10,
                "active": True,
                "questions": [
                    {
                        "text": "How snakey are Goldman people?",
                        "video_chat_url": "https://upenn.zoom.us/j/adadsf12313",
                        "status": Question.STATUS_ACTIVE,
                        "time_asked": now - datetime.timedelta(minutes=11),
                        "time_response_started": now - datetime.timedelta(minutes=5),
                        "should_send_up_soon_notification": False,
                    },
                    {
                        "text": "Can I get the recruiter's email?",
                        "video_chat_url": "https://upenn.zoom.us/j/ilovegoldmansachsplz",
                        "status": Question.STATUS_ASKED,
                        "time_asked": now - datetime.timedelta(minutes=20),
                        "should_send_up_soon_notification": False,
                    },
                    {
                        "text": "How much money do I get?",
                        "video_chat_url": "https://upenn.zoom.us/j/hellof",
                        "status": Question.STATUS_ANSWERED,
                        "time_asked": now - datetime.timedelta(minutes=40),
                        "time_response_started": now - datetime.timedelta(minutes=10),
                        "time_responded_to": now - datetime.timedelta(minutes=1),
                        "should_send_up_soon_notification": False,
                    },
                ],
                "video_chat_setting": Queue.VIDEO_REQUIRED,
            },
            {
                "name": "Morgan Stanley Questions",
                "description": "Wall Street 2 EZ",
                "archived": False,
                "estimated_wait_time": 0,
                "active": True,
                "questions": [],
                "video_chat_setting": Queue.VIDEO_REQUIRED,
            },
            {
                "name": "Questions for Rejects - Will always be closed",
                "description": "Drop the class",
                "archived": False,
                "estimated_wait_time": 0,
                "active": False,
                "questions": [],
                "video_chat_setting": Queue.VIDEO_REQUIRED,
            },
        ],
        "semester": {"year": 2020, "term": Semester.TERM_SUMMER},
        "archived": False,
        "invite_only": False,
    },
    {
        "course_code": "621",
        "department": "LABS",
        "course_title": "Penn Labs",
        "description": "Honestly just the best club ever.",
        "queues": [
            {
                "name": "Vibing Questions",
                "description": "Good Vibes? Join Here",
                "archived": False,
                "estimated_wait_time": 20,
                "active": True,
                "questions": [
                    {
                        "text": "How good are you guys?",
                        "video_chat_url": "https://upenn.zoom.us/j/adad13",
                        "status": Question.STATUS_WITHDRAWN,
                        "time_asked": now - datetime.timedelta(minutes=1),
                        "should_send_up_soon_notification": False,
                    },
                    {
                        "text": "I needa go pee.",
                        "video_chat_url": "https://upenn.zoom.us/j/dfsgfdsgfddskjf",
                        "status": Question.STATUS_REJECTED,
                        "time_asked": now - datetime.timedelta(minutes=91),
                        "time_response_started": now - datetime.timedelta(minutes=2),
                        "time_responded_to": now - datetime.timedelta(minutes=2),
                        "rejected_reason": "NOT_HERE",
                        "should_send_up_soon_notification": True,
                    },
                    {
                        "text": "Ying where's my DaRK mOdE",
                        "video_chat_url": "https://upenn.zoom.us/j/armaanTakeMyChildren",
                        "status": Question.STATUS_ACTIVE,
                        "time_asked": now - datetime.timedelta(minutes=400),
                        "time_response_started": now - datetime.timedelta(minutes=130),
                        "should_send_up_soon_notification": False,
                    },
                ],
                "video_chat_setting": Queue.VIDEO_REQUIRED,
            },
            {
                "name": "Other Questions",
                "description": "Questions for not so good vibes",
                "archived": False,
                "estimated_wait_time": 30,
                "active": True,
                "questions": [
                    {
                        "text": "Potatoes",
                        "video_chat_url": "https://upenn.zoom.us/j/ad123456sdfghd13",
                        "status": Question.STATUS_WITHDRAWN,
                        "time_asked": now - datetime.timedelta(minutes=1),
                        "should_send_up_soon_notification": False,
                    },
                    {
                        "text": "How's life at the Labs?",
                        "video_chat_url": "https://upenn.zoom.us/j/daaaarrkkkkkMooodddeee",
                        "status": Question.STATUS_ANSWERED,
                        "time_asked": now - datetime.timedelta(minutes=240),
                        "time_response_started": now - datetime.timedelta(minutes=50),
                        "time_responded_to": now - datetime.timedelta(minutes=17),
                        "should_send_up_soon_notification": True,
                    },
                ],
                "video_chat_setting": Queue.VIDEO_REQUIRED,
            },
            {
                "name": "We are archiving the bad vibes",
                "description": "No bad vibes allowed",
                "archived": True,
                "estimated_wait_time": 0,
                "active": False,
                "questions": [],
                "video_chat_setting": Queue.VIDEO_REQUIRED,
            },
        ],
        "semester": {"year": 2020, "term": Semester.TERM_SPRING},
        "archived": False,
        "invite_only": True,
    },
    {
        "course_code": "500",
        "department": "OLD",
        "course_title": "Class of 1930",
        "description": "Class of 1930 Graduates Only! Likely to be archived",
        "semester": {"year": 1930, "term": Semester.TERM_SPRING},
        "archived": True,
        "queues": [],
        "invite_only": False,
    },
]


class Command(BaseCommand):
    help = "Populates the development environment with dummy data."

    def handle(self, *args, **kwargs):

        if not settings.DEBUG:
            raise CommandError("You probably do not want to run this script in production!")

        # create 11 users
        # (1 prof, 2 head TA's, 2 TA's, 4 students, 1 invites, and 1 not in the course)
        count = 0
        schools = ["seas", "nursing", "wharton", "sas"]
        users = [
            "Benjamin Franklin",
            "George Washington",
            "John Adams",
            "Thomas Jefferson",
            "James Madison",
            "James Monroe",
            "John Quincy Adams",
            "Andrew Jackson",
            "Kevin Chen",
            "Justin Zhang",
            "Armaan Davis",
        ]
        user_objs = []
        for user in users:
            first, last = user.split(" ", 1)
            last = last.replace(" ", "")
            username = "{}{}".format(first[0], last).lower()
            email = "{}@{}.upenn.edu".format(username, schools[count % len(schools)])
            count += 1
            User = get_user_model()
            if User.objects.filter(username=username).exists():
                user_objs.append(User.objects.get(username=username))
            else:
                obj = User.objects.create_user(username, email, "test")
                obj.first_name = first
                obj.last_name = last
                obj.is_staff = True
                obj.set_password("pennlabs")
                obj.save()
                user_objs.append(obj)

        # create TJeff as superuser
        tjeff = user_objs[3]
        tjeff.is_superuser = True
        tjeff.save()

        # create profiles for each user
        for i in range(len(user_objs)):
            code = str(i) + "code"
            phone_number = "+1234567890" + str(i)[0]
            if i % 5 == 0:
                # create combo 1 - no sms verification, notifications not enabled
                newProfile = Profile.objects.get(user=user_objs[i])
                newProfile.phone_number = phone_number
            if i % 5 == 1:
                # create combo 2 - sms verfication pending, notifications disabled
                newProfile = Profile.objects.get(user=user_objs[i])
                newProfile.sms_verification_code = code
                newProfile.phone_number = phone_number
            if i % 5 == 2:
                # create combo 3 - sms verified and sms notifications off
                newProfile = Profile.objects.get(user=user_objs[i])
                newProfile.sms_verification_code = code
                newProfile.sms_verification_timestamp = now - datetime.timedelta(minutes=i * 10)
                newProfile.sms_verified = True
                newProfile.phone_number = phone_number
            if i % 5 == 3:
                # create combo 4 - sms verfied and notifications on
                newProfile = Profile.objects.get(user=user_objs[i])
                newProfile.sms_verification_code = code
                newProfile.sms_notifications_enabled = True
                newProfile.sms_verification_timestamp = now - datetime.timedelta(minutes=i * 10)
                newProfile.sms_verified = True
                newProfile.phone_number = phone_number

            newProfile.save()

        # create courses
        newCount = 0
        for info in courses:
            partial = dict(info)
            custom_fields = [
                "course_code",
                "queues",
            ]
            for field in custom_fields:
                if field in partial:
                    del partial[field]

            partial["semester"], _ = Semester.objects.get_or_create(
                year=partial["semester"]["year"], term=partial["semester"]["term"]
            )

            # created the course with everything except for memberships and membership invites
            newCourse, _ = Course.objects.get_or_create(
                course_code=info["course_code"], defaults=partial
            )

            # create 1 professor
            professorMembership, _ = Membership.objects.get_or_create(
                course=newCourse,
                user=user_objs[newCount % len(user_objs)],
                kind=Membership.KIND_PROFESSOR,
            )
            newCount += 1

            # create 2 head TAs
            headTAList = []
            for i in range(2):

                headTAMembership, _ = Membership.objects.get_or_create(
                    course=newCourse,
                    user=user_objs[(newCount) % len(user_objs)],
                    kind=Membership.KIND_HEAD_TA,
                )
                headTAList.append(headTAMembership)
                newCount += 1

                if i == 1:
                    headTAMembership.last_active = now - datetime.timedelta(minutes=2)
                    headTAMembership.save()

            # create 2 regular TA's
            regularTAList = []
            for i in range(2):
                regularTAMembership, _ = Membership.objects.get_or_create(
                    course=newCourse,
                    user=user_objs[(newCount) % len(user_objs)],
                    kind=Membership.KIND_TA,
                )
                regularTAList.append(regularTAMembership)
                newCount += 1

                if i == 1 or i == 3:
                    regularTAMembership.last_active = now - datetime.timedelta(minutes=i)
                    regularTAMembership.save()

            # list with head TA's and regular TA's
            totalTAList = headTAList + regularTAList

            # create 4 students
            studentList = []
            for i in range(4):
                studentMembership, _ = Membership.objects.get_or_create(
                    course=newCourse,
                    user=user_objs[(newCount) % len(user_objs)],
                    kind=Membership.KIND_STUDENT,
                )
                studentList.append(studentMembership)
                newCount += 1

            # create an invite per course
            membership_invite, _ = MembershipInvite.objects.get_or_create(
                email=user_objs[(newCount + 1) % len(user_objs)].email,
                course=newCourse,
                kind=Membership.KIND_CHOICES[(newCount + 1) % len(Membership.KIND_CHOICES)][0],
            )

            # create queues for each course
            for q in info["queues"]:
                newQueue, _ = Queue.objects.get_or_create(
                    name=q["name"],
                    description=q["description"],
                    course=newCourse,
                    archived=q["archived"],
                    estimated_wait_time=q["estimated_wait_time"],
                    active=q["active"],
                )

                respondedToCount = 0
                askedByCount = 0

                # adding the questions to each queue
                for ques in q["questions"]:

                    newQuestion, _ = Question.objects.get_or_create(
                        text=ques["text"],
                        queue=newQueue,
                        video_chat_url=ques["video_chat_url"],
                        status=ques["status"],
                        asked_by=studentList[askedByCount % len(studentList)].user,
                        should_send_up_soon_notification=ques["should_send_up_soon_notification"],
                    )
                    # prevent auto now add from changing the time
                    newQuestion.time_asked = ques["time_asked"]

                    askedByCount += 1

                    # accounting for different question status
                    if ques["status"] in [
                        Question.STATUS_REJECTED,
                        Question.STATUS_ANSWERED,
                        Question.STATUS_ACTIVE,
                    ]:
                        newQuestion.time_response_started = ques["time_response_started"]
                        newQuestion.responded_to_by = totalTAList[
                            respondedToCount % len(totalTAList)
                        ].user
                        respondedToCount += 1

                    if ques["status"] == Question.STATUS_REJECTED:
                        newQuestion.rejected_reason = ques["rejected_reason"]

                    if ques["status"] in [Question.STATUS_ANSWERED, Question.STATUS_REJECTED]:
                        newQuestion.time_responded_to = ques["time_responded_to"]

                    newQuestion.save()

        call_command("queue_daily_stat", "--hist")
        call_command("queue_heatmap_stat", "--hist")
