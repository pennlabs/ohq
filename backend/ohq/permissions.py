from django.db.models import Q
from rest_framework import permissions
from schedule.models import Event, EventRelation, Occurrence

from ohq.models import Course, Membership, Question


# Hierarchy of permissions is usually:
# Professor > Head TA > TA > Student > User
# Anonymous Users can't do anything
# Note: everything other than IsSuperuser and CoursePermission is
# scoped to a specific course.


class IsSuperuser(permissions.BasePermission):
    """
    Grants permission if the current user is a superuser.
    """

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user.is_superuser

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser


class CoursePermission(permissions.BasePermission):
    """
    Anyone can get or list courses.
    Only head TAs or professors should be able to modify a course.
    Current Head TAs+ or faculty members can create courses.
    No one can delete courses.
    """

    def has_object_permission(self, request, view, obj):
        # Anyone can get a single course
        if view.action == "retrieve":
            return True

        membership = Membership.objects.filter(course=obj, user=request.user).first()

        # Non members can't do anything other than retrieve a course
        if membership is None:
            return False

        # No one can delete a course
        if view.action == "destroy":
            return False

        # Course leadership can make changes
        if view.action in ["update", "partial_update"]:
            return membership.is_leadership and not obj.archived

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        # Members can list courses
        if view.action == "list":
            return True

        if view.action == "create":
            return (
                request.user.groups.filter(name="platform_faculty").exists()
                or Membership.objects.filter(
                    user=request.user, kind=Membership.KIND_HEAD_TA
                ).exists()
                or Membership.objects.filter(
                    user=request.user, kind=Membership.KIND_PROFESSOR
                ).exists()
            )

        return True


class QueuePermission(permissions.BasePermission):
    """
    TAs+ should be able to modify a course.
    Only head TAs or professors can create or delete queues.
    Students+ can get or list queues
    """

    def has_object_permission(self, request, view, obj):
        membership = Membership.objects.get(course=view.kwargs["course_pk"], user=request.user)

        # Students+ can get a single queue
        if view.action == "retrieve":
            return True

        # TAs+ can make changes
        if view.action in ["update", "partial_update", "clear"]:
            return membership.is_ta and not obj.archived

        # Head TAs+ can create or delete a queue
        if view.action == "destroy":
            return membership.is_leadership

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # Non-Students can't do anything
        if membership is None:
            return False

        # TAs+ can make changes
        if view.action in ["update", "partial_update"]:
            return membership.is_ta

        # Head TAs+ can create or delete a queue
        if view.action == "create":
            return membership.is_leadership

        return True


class QuestionPermission(permissions.BasePermission):
    """
    Students can create questions
    Students can get, list, or modify their own questions.
    TAs+ can list questions and modify any question.
    No one can delete questions.
    """

    def has_object_permission(self, request, view, obj):
        membership = Membership.objects.get(course=view.kwargs["course_pk"], user=request.user)

        # Students can get or modify their own question
        # TAs+ can get or modify any questions
        if view.action in ["retrieve", "update", "partial_update", "position"]:
            return obj.asked_by == request.user or membership.is_ta

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # Non-Students can't do anything
        if membership is None:
            return False

        # No one can delete questions
        if view.action == "destroy":
            return False

        # Students can view their last asked question:
        if view.action in ["last", "quota_count"]:
            return membership.kind == Membership.KIND_STUDENT

        # Students can only create 1 question per queue
        if view.action == "create":
            existing_question = Question.objects.filter(
                Q(queue=view.kwargs["queue_pk"])
                & Q(asked_by=request.user)
                & (Q(status=Question.STATUS_ASKED) | Q(status=Question.STATUS_ACTIVE))
            ).first()

            return membership.kind == Membership.KIND_STUDENT and existing_question is None

        # Students+ can get, list, or modify questions
        # With restrictions defined in has_object_permission
        return True


class QuestionSearchPermission(permissions.BasePermission):
    """
    TAs+ can list questions.
    """

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # Non-Students can't do anything
        if membership is None:
            return False

        # TAs+ can list questions
        return membership.is_ta


class MembershipPermission(permissions.BasePermission):
    """
    Students can get their own membership.
    TAs+ can list memberships.
    Users can create a Student membership with open courses.
    Head TAs+ can modify and delete memberships.
    Students can delete their own memberships.
    """

    def has_object_permission(self, request, view, obj):
        membership = Membership.objects.get(course=view.kwargs["course_pk"], user=request.user)

        # Students can get their own memberships
        # TAs+ can get any memberships
        if view.action == "retrieve":
            return obj.user == request.user or membership.is_ta

        # Students can delete their own memberships
        # Head TAs+ can delete any memberships
        # TODO: make sure Head TAs+ can't delete professors
        # and professors can't delete themselves
        if view.action == "destroy":
            return obj.user == request.user or membership.is_leadership

        # Head TAs+ can modify any membership
        # TODO: make sure Head TAs+ can't delete professors
        # and professors can't delete themselves
        if view.action in ["update", "partial_update"]:
            return membership.is_leadership

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # No one can create a membership
        if view.action == "create":
            course = Course.objects.get(id=view.kwargs["course_pk"])
            return membership is None and not course.invite_only

        # Non-Students can't do anything besides create a membership
        if membership is None:
            return False

        # Students+ can get, modify, and delete memberships
        # can list memberships of leaders.
        # With restrictions defined in has_object_permission
        return True


class MembershipInvitePermission(permissions.BasePermission):
    """
    TAs+ can get and list membership invites.
    Head TAs+ can create, modify, and delete memberships.
    """

    def has_object_permission(self, request, view, obj):
        membership = Membership.objects.get(course=view.kwargs["course_pk"], user=request.user)

        # TAs+ can get any membership invite
        if view.action == "retrieve":
            return membership.is_ta

        # Head TAs+ can modify or delete any memberships
        if view.action in ["destroy", "update", "partial_update"]:
            return membership.is_leadership

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # Non-Students can't do anything
        if membership is None:
            return False

        # Head TAs+ can create membership invites
        if view.action == "create":
            return membership.is_leadership

        # TAs+ can list membership invites
        if view.action == "list":
            return membership.is_ta

        # TAs+ can get, modify, and delete memberships
        # With restrictions defined in has_object_permission
        return membership.is_ta


class MassInvitePermission(permissions.BasePermission):
    """
    Head TAs+ can create mass membership invites.
    """

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # Non-Students can't do anything
        if membership is None:
            return False

        return membership.is_leadership


class CourseStatisticPermission(permissions.BasePermission):
    """
    TA+ can access course related statistics
    """

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        membership = (
            Membership.objects.filter(course=view.kwargs["course_pk"], user=request.user)
            .exclude(kind=Membership.KIND_STUDENT)
            .first()
        )

        # anyone who is an instructor of the class can see course related statistics
        return membership is not None


class QueueStatisticPermission(permissions.BasePermission):
    """
    Students+ can access queue related statistics
    """

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # anyone who is a member of the class can see queue related statistics
        return membership is not None


class AnnouncementPermission(permissions.BasePermission):
    """
    TAs+ can create/update/delete announcements
    Students can get/list announcements
    """

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # Non-Students can't do anything
        if membership is None:
            return False

        # Students+ can get/list announcements
        if view.action in ["list", "retrieve"]:
            return True

        # TAs+ can create, modify, and delete announcements
        return membership.is_ta


class TagPermission(permissions.BasePermission):
    """
    Head TAs+ should be able to create, modify and delete a tag.
    Students+ can get or list tags.
    """

    def has_object_permission(self, request, view, obj):
        membership = Membership.objects.get(course=view.kwargs["course_pk"], user=request.user)

        # Students+ can get a single tag
        if view.action == "retrieve":
            return True

        # Head TAs+ can make changes
        if view.action in ["destroy", "partial_update", "update"]:
            return membership.is_leadership

    def has_permission(self, request, view):
        # Anonymous users can't do anything
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # Non-Students can't do anything
        if membership is None:
            return False

        if view.action in ["list", "retrieve"]:
            return True

        # Head TAs+ can make changes
        if view.action in ["create", "destroy", "update", "partial_update"]:
            return membership.is_leadership


class EventPermission(permissions.BasePermission):
    def get_membership_from_event(self, request, event):
        event_course_relation = EventRelation.objects.filter(event=event).first()
        membership = Membership.objects.filter(
            course_id=event_course_relation.object_id, user=request.user
        ).first()
        return membership

    def has_object_permission(self, request, view, obj):
        if view.action in ["partial_update", "update"]:
            event = Event.objects.filter(pk=view.kwargs["pk"]).first()
            membership = self.get_membership_from_event(request, event)
            if membership is None:
                return False
            return membership.is_ta

        if view.action in ["retrieve", "destroy"]:
            event = Event.objects.filter(pk=view.kwargs["pk"]).first()
            membership = self.get_membership_from_event(request, event)
            if membership is None:
                return False

            return (view.action == "retrieve") or (view.action == "destroy" and membership.is_ta)

        return False

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Anonymous users can't do anything
        if view.action in ["create"]:
            course_pk = request.data.get("course_id", None)
            if course_pk is None:
                return False

            course = Course.objects.get(pk=course_pk)
            membership = Membership.objects.filter(course=course, user=request.user).first()
            if membership is None:
                return False
            return membership.is_ta

        if view.action in ["list"]:
            course_ids = request.GET.getlist("course")
            for course in course_ids:
                membership = Membership.objects.filter(course=course, user=request.user).first()
                if membership is None:
                    return False
            return True

        return True


class OccurrencePermission(permissions.BasePermission):
    def get_membership_from_event(self, request, event):
        event_course_relation = EventRelation.objects.filter(event=event).first()
        membership = Membership.objects.filter(
            course_id=event_course_relation.object_id, user=request.user
        ).first()
        return membership

    def has_object_permission(self, request, view, obj):
        if view.action in ["retrieve"]:
            occurrence = Occurrence.objects.filter(pk=view.kwargs["pk"]).first()
            membership = self.get_membership_from_event(request=request, event=occurrence.event)
            return membership is not None

        if view.action in ["update", "partial_update"]:
            occurrence = Occurrence.objects.filter(pk=view.kwargs["pk"]).first()
            membership = self.get_membership_from_event(request, occurrence.event)
            return membership is not None and membership.is_ta

        return False

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if view.action in ["list"]:
            # if any member of the course in the list is not accessible, return false
            course_ids = request.GET.getlist("course")
            for course in course_ids:
                membership = Membership.objects.filter(course=course, user=request.user).first()
                if membership is None:
                    return False
            return True

        return True

class DocumentCreatePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        return membership.is_leadership

        # # Non-Students can't do anything
        # if membership is None:
        #     return False

        # if view.action == "retrieve":
        #     return membership.is_ta or membership.is_leadership

        # # Head TAs+ can make changes
        # if view.action in ["create", "destroy", "update", "partial_update"]:
        #     return membership.is_leadership

class DocumentPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        
        membership = Membership.objects.get(course=view.kwargs["course_pk"], user=request.user)

        if view.action == "retrieve":
            return membership.is_ta or membership.is_leadership

        if view.action in ["create", "destroy", "partial_update", "update"]:
            return membership.is_leadership
        
        return False

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # Non-Students can't do anything
        if membership is None:
            return False

        if view.action == "retrieve":
            return membership.is_ta or membership.is_leadership

        # Head TAs+ can make changes
        if view.action in ["create", "destroy", "update", "partial_update"]:
            return membership.is_leadership
        
class VectorSearchPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        return membership.is_ta or membership.is_leadership

        # # Non-Students can't do anything
        # if membership is None:
        #     return False

        # if view.action == "retrieve":
        #     return membership.is_ta or membership.is_leadership

        # # Head TAs+ can make changes
        # if view.action in ["create", "destroy", "update", "partial_update"]:
        #     return membership.is_leadership
    
class VectorDBPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):

        membership = Membership.objects.get(course=view.kwargs["course_pk"], user=request.user)

        if view.action == "retrieve":
            return membership.is_ta or membership.is_leadership

        if view.action in ["create", "destroy", "partial_update", "update"]:
            return membership.is_leadership
        
        return False

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        membership = Membership.objects.filter(
            course=view.kwargs["course_pk"], user=request.user
        ).first()

        # Non-Students can't do anything
        if membership is None:
            return False

        if view.action == "retrieve":
            return membership.is_ta or membership.is_leadership

        # Head TAs+ can make changes
        if view.action in ["create", "destroy", "update", "partial_update"]:
            return membership.is_leadership