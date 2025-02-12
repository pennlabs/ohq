from django.urls import path
from rest_framework_nested import routers
from rest_live.routers import RealtimeRouter

from ohq.views import (
    AnnouncementViewSet,
    CourseStatisticView,
    CourseViewSet,
    EventViewSet,
    MassInviteView,
    MembershipInviteViewSet,
    MembershipViewSet,
    OccurrenceViewSet,
    QuestionSearchView,
    QuestionViewSet,
    QueueStatisticView,
    QueueViewSet,
    ResendNotificationView,
    SemesterViewSet,
    TagViewSet,
    UserView,
    BookingViewSet,
)


app_name = "ohq"

router = routers.SimpleRouter()
router.register("semesters", SemesterViewSet, basename="semester")
router.register("courses", CourseViewSet, basename="course")
router.register("events", EventViewSet, basename="event")
router.register("occurrences", OccurrenceViewSet, basename="occurrence")
router.register("bookings", BookingViewSet, basename="booking")

course_router = routers.NestedSimpleRouter(router, "courses", lookup="course")
course_router.register("queues", QueueViewSet, basename="queue")
course_router.register("members", MembershipViewSet, basename="member")
course_router.register("invites", MembershipInviteViewSet, basename="invite")
course_router.register("announcements", AnnouncementViewSet, basename="announcement")
course_router.register("tags", TagViewSet, basename="tag")

queue_router = routers.NestedSimpleRouter(course_router, "queues", lookup="queue")
queue_router.register("questions", QuestionViewSet, basename="question")

realtime_router = RealtimeRouter()
realtime_router.register(QuestionViewSet)
realtime_router.register(AnnouncementViewSet)

additional_urls = [
    path("accounts/me/", UserView.as_view(), name="me"),
    path("accounts/me/resend/", ResendNotificationView.as_view(), name="resend"),
    path("courses/<slug:course_pk>/mass-invite/", MassInviteView.as_view(), name="mass-invite"),
    path(
        "courses/<slug:course_pk>/questions/", QuestionSearchView.as_view(), name="questionsearch"
    ),
    path(
        "courses/<slug:course_pk>/queues/<slug:queue_pk>/statistics/",
        QueueStatisticView.as_view(),
        name="queue-statistic",
    ),
    path(
        "courses/<slug:course_pk>/course-statistics/",
        CourseStatisticView.as_view(),
        name="course-statistic",
    ),
]

urlpatterns = router.urls + course_router.urls + queue_router.urls + additional_urls
