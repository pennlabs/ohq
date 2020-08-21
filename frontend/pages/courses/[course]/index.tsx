import React from "react";
import { useRouter } from "next/router";
import Course from "../../../components/Course/Course";
import { withAuth } from "../../../context/auth";
import { doApiRequest } from "../../../utils/fetch";
import { isLeadershipRole } from "../../../utils/enums";

const CoursePage = (props) => {
    const router = useRouter();
    const { course: courseId } = router.query;
    const { course, memberships, invites, leadership } = props;
    return (
        <Course
            // TODO: better fix
            // @ts-ignore
            courseId={parseInt(courseId)}
            course={course}
            memberships={memberships}
            invites={invites}
            leadership={leadership}
        />
    );
};

CoursePage.getInitialProps = async (context) => {
    const { query, req } = context;
    const data = {
        headers: req ? { cookie: req.headers.cookie } : undefined,
    };

    const [course, memberships, invites, leadership] = await Promise.all([
        doApiRequest(`/courses/${query.course}/`, data).then((res) =>
            res.json()
        ),
        doApiRequest(`/courses/${query.course}/members/`, data).then((res) =>
            res.json()
        ),
        doApiRequest(`/courses/${query.course}/invites/`, data).then((res) =>
            res.json()
        ),
        doApiRequest(`/courses/${query.course}/members/`, data).then((res) =>
            res.json()
        ),
    ]);
    return {
        course,
        memberships,
        invites,
        leadership: leadership.filter((m) => isLeadershipRole(m.kind)),
    };
};
export default withAuth(CoursePage);
