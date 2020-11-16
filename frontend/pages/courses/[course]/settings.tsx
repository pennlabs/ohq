import React from "react";
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

const SettingsPage = (props: CoursePageProps) => {
    const { course, leadership, tags } = props;
    return (
        <>
            <Head>
                <title>{`OHQ | ${course.department} ${course.courseCode}`}</title>
            </Head>
            <Grid columns="equal" divided style={{ width: "100%" }} stackable>
                <CourseWrapper
                    course={course}
                    leadership={leadership}
                    tags={tags}
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
): Promise<CoursePageProps> => {
    const { query, req } = context;
    const data = {
        headers: req ? { cookie: req.headers.cookie } : undefined,
    };

    let course: Course;
    let leadership: Membership[];
    let tags: Tag[];

    const response = await doMultipleSuccessRequests([
        { path: `/courses/${query.course}/`, data },
        { path: `/courses/${query.course}/members/`, data },
        { path: `/courses/${query.course}/tags/`, data },
    ]);

    if (response.success) {
        [course, leadership, tags] = response.data;
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
