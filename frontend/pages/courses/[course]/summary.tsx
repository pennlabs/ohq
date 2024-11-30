import Head from "next/head";
import { Grid } from "semantic-ui-react";
import { NextPageContext } from "next";
import CourseWrapper from "../../../components/Course/CourseWrapper";
import { withAuth } from "../../../context/auth";
import staffCheck from "../../../utils/staffcheck";
import { withProtectPage } from "../../../utils/protectpage";
import { doMultipleSuccessRequests } from "../../../utils/fetch";
import { isLeadershipRole } from "../../../utils/enums";
import { CoursePageProps, Course, Membership } from "../../../types";
import Summary from "../../../components/Course/Summary/Summary";
import { QuestionListResult } from "../../../hooks/data-fetching/questionsummary";
import nextRedirect from "../../../utils/redirect";

interface SummaryPageProps extends CoursePageProps {
    questionListResult: QuestionListResult;
}
const SummaryPage = (props: SummaryPageProps) => {
    const { course, leadership, questionListResult } = props;
    return (
        <>
            <Head>
                <title>{`OHQ | ${course.department} ${course.courseCode} | Question Summary`}</title>
            </Head>
            <Grid columns="equal" divided style={{ width: "100%" }} stackable>
                <CourseWrapper
                    course={course}
                    leadership={leadership}
                    render={() => {
                        return (
                            <Summary
                                course={course}
                                questionListResult={questionListResult}
                            />
                        );
                    }}
                />
            </Grid>
        </>
    );
};

SummaryPage.getInitialProps = async (
    context: NextPageContext
): Promise<SummaryPageProps> => {
    const { query, req } = context;
    const data = {
        headers: req ? { cookie: req.headers.cookie } : undefined,
    };

    let course: Course;
    let leadership: Membership[];
    let questionListResult: QuestionListResult;

    const response = await doMultipleSuccessRequests([
        { path: `/api/courses/${query.course}/`, data },
        { path: `/api/courses/${query.course}/members/`, data },
        {
            path: `/api/courses/${query.course}/questions/?order_by=-time_asked`,
            data,
        },
    ]);

    if (response.success) {
        [course, leadership, questionListResult] = response.data;
    } else {
        nextRedirect(context, () => true, "/404");
        throw new Error("Next should redirect: unreachable");
    }

    return {
        course,
        leadership: leadership.filter((m) => isLeadershipRole(m.kind)),
        questionListResult,
    };
};

export default withProtectPage(withAuth(SummaryPage), (user, ctx) => {
    return staffCheck(user, ctx);
});
