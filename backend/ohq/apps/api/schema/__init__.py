import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from ohq.apps.api.schema import account, courses, queues, feedback_questions, questions, types

from ohq.apps.api.models import Course, CourseUser


class Query(graphene.ObjectType):

    current_user = graphene.Field(types.UserNode)

    def resolve_current_user(self, info):
        return info.context.user.get_user()

    # User search for invitation
    invitable_users = DjangoFilterConnectionField(types.UserMetaNode)

    # course_user = graphene.Field(CourseUserNode)
    # course_users = DjangoFilterField(CourseUserNode)

    # courses = graphene.List(CourseNode)
    # courses = DjangoFilterField(CourseNode)

    course = relay.Node.Field(types.CourseNode)

    # Course search for students joining
    joinable_courses = DjangoFilterConnectionField(types.CourseMetaNode)

    def resolve_joinable_courses(self, info, **kwargs):
        course_ids = (
            CourseUser.objects
                .filter(user=info.context.user.get_user())
                .values_list('course_id', flat=True)
        )
        return Course.objects.exclude(id__in=course_ids).filter(invite_only=False, **kwargs)

    queue = relay.Node.Field(types.QueueNode)


class Mutation(graphene.ObjectType):
    create_user = account.CreateUser.Field()
    update_user = account.UpdateUser.Field()

    create_course = courses.CreateCourse.Field()

    create_queue = queues.CreateQueue.Field()
    update_queue = queues.UpdateQueue.Field()

    create_short_answer_feedback_question = (
        feedback_questions.CreateShortAnswerFeedbackQuestion.Field()
    )
    create_radio_button_feedback_question = (
        feedback_questions.CreateRadioButtonFeedbackQuestion.Field()
    )
    create_slider_feedback_question = (
        feedback_questions.CreateSliderFeedbackQuestion.Field()
    )
    answer_feedback_questions = feedback_questions.AnswerFeedbackQuestions.Field()

    create_question = questions.CreateQuestion.Field()
    withdraw_question = questions.WithdrawQuestion.Field()
    reject_question = questions.RejectQuestion.Field()
    start_question = questions.StartQuestion.Field()
    finish_question = questions.FinishQuestion.Field()

    add_user_to_course = courses.AddUserToCourse.Field()
    remove_user_from_course = courses.RemoveUserFromCourse.Field()
    join_course = courses.JoinCourse.Field()
    invite_email = courses.InviteEmail.Field()
