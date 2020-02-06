from datetime import datetime

from graphql_relay.node.node import from_global_id

from django.db import transaction

from ohq.apps.api.schema.types import *


class CreateQuestionInput(graphene.InputObjectType):
    queue_id = graphene.ID(required=True)
    text = graphene.String(required=True)
    tags = graphene.List(graphene.String, required=True)


class CreateQuestionResponse(graphene.ObjectType):
    question = graphene.Field(QuestionNode)


class CreateQuestion(graphene.Mutation):
    class Arguments:
        input = CreateQuestionInput(required=True)

    Output = CreateQuestionResponse

    @staticmethod
    def mutate(root, info, input):
        with transaction.atomic():
            user = info.context.user.get_user()
            queue = Queue.objects.get(pk=from_global_id(input.queue_id)[1])
            course = queue.course
            if not CourseUser.objects.filter(
                user=user,
                course=course,
                kind=CourseUserKind.STUDENT.name,
            ).exists():
                raise PermissionError
            # Check for any other unanswered questions in this course
            if Question.objects.filter(
                user=user,
                course=course,
                time_answered__isnull=True,
            ).exists():
                raise ValueError
            # TODO limit number of questions asked
            if any(tag not in course.tags for tag in input.tags):
                raise ValueError
            question = Question.objects.create(
                queue=queue,
                text=input.text,
                tags=input.tags,
                asked_by=user,
            )

        return CreateQuestionResponse(question=question)


class WithdrawQuestionInput(graphene.InputObjectType):
    question_id = graphene.ID(required=True)


class WithdrawQuestionResponse(graphene.ObjectType):
    question = graphene.Field(QuestionNode)


class WithdrawQuestion(graphene.Mutation):
    class Arguments:
        input = WithdrawQuestionInput(required=True)

    Output = WithdrawQuestionResponse

    @staticmethod
    def mutate(root, info, input):
        with transaction.atomic():
            user = info.context.user.get_user()
            question = Question.objects.get(pk=from_global_id(input.question_id)[1])
            # if not CourseUser.objects.filter(
            #     user=user,
            #     course=question.queue.course,
            #     kind__in=CourseUserKind.student.name,
            # ).exists():
            #     raise PermissionError
            if question.asked_by != user:
                raise PermissionError
            if question.time_started or question.time_rejected:
                raise ValueError

            question.time_withdrawn = datetime.now()
            question.save()

        return WithdrawQuestionResponse(question=question)


class RejectQuestionInput(graphene.InputObjectType):
    question_id = graphene.ID(required=True)
    rejected_reason = graphene.Field(QuestionRejectionReasonType, required=True)
    rejected_reason_other = graphene.String(required=False)


class RejectQuestionResponse(graphene.ObjectType):
    question = graphene.Field(QuestionNode)


class RejectQuestion(graphene.Mutation):
    class Arguments:
        input = RejectQuestionInput(required=True)

    Output = RejectQuestionResponse

    @staticmethod
    def mutate(root, info, input):
        with transaction.atomic():
            user = info.context.user.get_user()
            question = Question.objects.get(pk=from_global_id(input.question_id)[1])
            if not CourseUser.objects.filter(
                user=user,
                course=question.queue.course,
                kind__in=CourseUserKind.staff(),
            ).exists():
                raise PermissionError
            if (
                (input.rejected_reason == QuestionRejectionReason.OTHER.name and
                 input.rejected_reason_other is None) or
                (input.rejected_reason != QuestionRejectionReason.OTHER.name and
                 input.rejected_reason_other is not None)
            ):
                raise ValueError
            question.rejected_reason = input.rejected_reason
            question.rejected_reason_other = input.rejected_reason_other
            question.rejected_by = user
            question.time_rejected = datetime.now()
            question.save()

        return RejectQuestionResponse(question=question)


class StartQuestionInput(graphene.InputObjectType):
    question_id = graphene.ID(required=True)


class StartQuestionResponse(graphene.ObjectType):
    question = graphene.Field(QuestionNode)


class StartQuestion(graphene.Mutation):
    class Arguments:
        input = StartQuestionInput(required=True)

    Output = StartQuestionResponse

    @staticmethod
    def mutate(root, info, input):
        with transaction.atomic():
            user = info.context.user.get_user()
            question = Question.objects.get(pk=from_global_id(input.question_id)[1])
            if not CourseUser.objects.filter(
                user=user,
                course=question.queue.course,
                kind__in=CourseUserKind.staff(),
            ).exists():
                raise PermissionError
            if question.time_withdrawn:
                raise ValueError
            question.time_started = datetime.now()
            question.answered_by = user
            question.save()

        return StartQuestionResponse(question=question)


class UndoStartQuestionInput(graphene.InputObjectType):
    question_id = graphene.ID(required=True)


class UndoStartQuestionResponse(graphene.ObjectType):
    question = graphene.Field(QuestionNode)


class UndoStartQuestion(graphene.Mutation):
    class Arguments:
        input = UndoStartQuestionInput(required=True)

    Output = UndoStartQuestionResponse

    @staticmethod
    def mutate(root, info, input):
        with transaction.atomic():
            user = info.context.user.get_user()
            question = Question.objects.get(pk=from_global_id(input.question_id)[1])
            if not CourseUser.objects.filter(
                    user=user,
                    course=question.queue.course,
                    kind__in=CourseUserKind.staff(),
            ).exists():
                raise PermissionError
            if question.time_withdrawn:
                raise ValueError
            question.time_started = None
            question.answered_by = None
            question.save()

        return UndoStartQuestionResponse(question=question)


class FinishQuestionInput(graphene.InputObjectType):
    question_id = graphene.ID(required=True)


class FinishQuestionResponse(graphene.ObjectType):
    question = graphene.Field(QuestionNode)


class FinishQuestion(graphene.Mutation):
    class Arguments:
        input = FinishQuestionInput(required=True)

    Output = FinishQuestionResponse

    @staticmethod
    def mutate(root, info, input):
        with transaction.atomic():
            user = info.context.user.get_user()
            question = Question.objects.get(pk=from_global_id(input.question_id)[1])
            # if not CourseUser.objects.filter(
            #     user=user,
            #     course=question.queue.course,
            #     kind__in=CourseUserKind.staff(),
            # ).exists():
            #     raise PermissionError
            if question.answered_by != user:
                raise PermissionError
            question.time_answered = datetime.now()
            question.save()

        return FinishQuestionResponse(question=question)
