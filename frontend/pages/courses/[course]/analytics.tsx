import Head from "next/head";
import { Grid } from "semantic-ui-react";
import { NextPageContext } from "next";
import CourseWrapper from "../../../components/Course/CourseWrapper";
import { withAuth } from "../../../context/auth";
import staffCheck from "../../../utils/staffcheck";
import { withProtectPage } from "../../../utils/protectpage";
import { doMultipleSuccessRequests } from "../../../utils/fetch";
import { isLeadershipRole } from "../../../utils/enums";
import nextRedirect from "../../../utils/redirect";
import { Course, Membership, Queue } from "../../../types";
import Analytics from "../../../components/Course/Analytics/Analytics";

interface AnalyticsPageProps {
    course: Course;
    leadership: Membership[];
    queues: Queue[];
}

const AnalyticsPage = (props: AnalyticsPageProps) => {
    const { course, leadership, queues } = props;
    return (
        <>
            <Head>
                <title>{`OHQ | ${course.department} ${course.courseCode} | Analytics`}</title>
            </Head>
            <Grid columns="equal" divided style={{ width: "100%" }} stackable>
                <CourseWrapper
                    course={course}
                    leadership={leadership}
                    render={() => {
                        return <Analytics course={course} queues={queues} />;
                    }}
                />
            </Grid>
        </>
    );
};

AnalyticsPage.getInitialProps = async (
    context: NextPageContext
): Promise<AnalyticsPageProps> => {
    const { query, req } = context;
    const data = {
        headers: req ? { cookie: req.headers.cookie } : undefined,
    };

    let course: Course;
    let leadership: Membership[];
    let queues: Queue[];

    const response = await doMultipleSuccessRequests([
        { path: `/api/courses/${query.course}/`, data },
        { path: `/api/courses/${query.course}/members/`, data },
        { path: `/api/courses/${query.course}/queues/`, data },
    ]);

    if (response.success) {
        [course, leadership, queues] = response.data;
    } else {
        nextRedirect(context, () => true, "/404");
        throw new Error("Next should redirect: unreachable");
    }

    return {
        course,
        leadership: leadership.filter((m) => isLeadershipRole(m.kind)),
        queues,
    };
};

export default withProtectPage(withAuth(AnalyticsPage), (user, ctx) => {
    return staffCheck(user, ctx);
});
