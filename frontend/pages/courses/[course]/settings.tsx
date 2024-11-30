import Head from "next/head";
import { Grid } from "semantic-ui-react";
import { NextPageContext } from "next";
import CourseWrapper from "../../../components/Course/CourseWrapper";
import { withAuth } from "../../../context/auth";
import staffCheck from "../../../utils/staffcheck";
import { withProtectPage } from "../../../utils/protectpage";
import { doMultipleSuccessRequests } from "../../../utils/fetch";
import { isLeadershipRole } from "../../../utils/enums";
import CourseSettings from "../../../components/Course/CourseSettings/CourseSettings";
import { CoursePageProps, Course, Membership, Tag } from "../../../types";
import nextRedirect from "../../../utils/redirect";

interface SettingsPageProps extends CoursePageProps {
    tags: Tag[];
}

const SettingsPage = (props: SettingsPageProps) => {
    const { course, leadership, tags } = props;
    return (
        <>
            <Head>
                <title>{`OHQ | ${course.department} ${course.courseCode} | Settings`}</title>
            </Head>
            <Grid columns="equal" divided style={{ width: "100%" }} stackable>
                <CourseWrapper
                    course={course}
                    leadership={leadership}
                    render={() => {
                        return <CourseSettings course={course} tags={tags} />;
                    }}
                />
            </Grid>
        </>
    );
};

SettingsPage.getInitialProps = async (
    context: NextPageContext
): Promise<SettingsPageProps> => {
    const { query, req } = context;
    const data = {
        headers: req ? { cookie: req.headers.cookie } : undefined,
    };

    let course: Course;
    let leadership: Membership[];
    let tags: Tag[];

    const response = await doMultipleSuccessRequests([
        { path: `/api/courses/${query.course}/`, data },
        { path: `/api/courses/${query.course}/members/`, data },
        { path: `/api/courses/${query.course}/tags/`, data },
    ]);

    if (response.success) {
        [course, leadership, tags] = response.data;

        if (course.archived) {
            nextRedirect(
                context,
                () => true,
                `/courses/${query.course}/roster`
            );
        }
    } else {
        nextRedirect(context, () => true, "/404");
        throw new Error("Next should redirect: unreachable");
    }

    return {
        course,
        leadership: leadership.filter((m) => isLeadershipRole(m.kind)),
        tags,
    };
};

export default withProtectPage(withAuth(SettingsPage), (user, ctx) => {
    return staffCheck(user, ctx);
});
