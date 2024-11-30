import { useContext } from "react";
import { Segment, Menu, Image, Icon } from "semantic-ui-react";
import { useRouter } from "next/router";
import Link from "next/link";

import { AuthUserContext } from "../../context/auth";
import { useStaff } from "../../hooks/data-fetching/course";
import { Course } from "../../types";

interface CourseSidebarProps {
    course: Course;
}
const CourseSidebarNav = (props: CourseSidebarProps) => {
    const { course } = props;
    const courseId = course.id;

    const { user: initialUser } = useContext(AuthUserContext);
    if (!initialUser) {
        throw new Error(
            "Invariant broken, withAuth must be used with component"
        );
    }

    const { leader, staff } = useStaff(courseId, initialUser);

    const noWrapStyle = {
        whiteSpace: "nowrap",
        textOverflow: "ellipsis",
        overflow: "hidden",
    };

    const router = useRouter();

    return (
        <Segment basic>
            <Link href="/" as="/" legacyBehavior>
                <Image
                    src="../../../ohq.png"
                    size="tiny"
                    style={{ marginTop: "10px", cursor: "pointer" }}
                />
            </Link>
            <Menu vertical secondary fluid>
                {!course.archived && (
                    <Link
                        href="/courses/[course]"
                        as={`/courses/${courseId}`}
                        legacyBehavior
                    >
                        <Menu.Item
                            style={noWrapStyle}
                            name="Queues"
                            icon="hourglass one"
                            active={router.pathname.endsWith("[course]")}
                            color="blue"
                        />
                    </Link>
                )}
                {staff && (
                    <Link
                        href="/courses/[course]/calendar"
                        as={`/courses/${courseId}/calendar`}
                        legacyBehavior
                    >
                        <Menu.Item
                            style={noWrapStyle}
                            name="Calendar"
                            icon="calendar"
                            active={router.pathname.endsWith("calendar")}
                            color="blue"
                        />
                    </Link>
                )}
                {staff && (
                    <Link
                        href="/courses/[course]/roster"
                        as={`/courses/${courseId}/roster`}
                        legacyBehavior
                    >
                        <Menu.Item
                            style={noWrapStyle}
                            name="Roster"
                            icon="users"
                            active={router.pathname.endsWith("roster")}
                            color="blue"
                        />
                    </Link>
                )}
                {!course.archived && (
                    <Link
                        href="/courses/[course]/analytics"
                        as={`/courses/${courseId}/analytics`}
                        legacyBehavior
                    >
                        <Menu.Item
                            style={noWrapStyle}
                            active={router.pathname.endsWith("analytics")}
                            color="blue"
                        >
                            <Icon
                                name="chart bar"
                                style={{
                                    float: "right",
                                    margin: "0 0 0 .5em",
                                }}
                            />
                            Analytics
                        </Menu.Item>
                    </Link>
                )}
                {staff && (
                    <Link
                        href="/courses/[course]/summary"
                        as={`/courses/${courseId}/summary`}
                        legacyBehavior
                    >
                        <Menu.Item
                            style={noWrapStyle}
                            name="Question Summary"
                            icon="list ol"
                            active={router.pathname.endsWith("summary")}
                            color="blue"
                        />
                    </Link>
                )}
                {!course.archived && leader && (
                    <Link
                        href="/courses/[course]/settings"
                        as={`/courses/${courseId}/settings`}
                        legacyBehavior
                    >
                        <Menu.Item
                            style={noWrapStyle}
                            name="Course Settings"
                            icon="settings"
                            href={`/courses/${courseId}/settings`}
                            active={router.pathname.endsWith("settings")}
                            color="blue"
                        />
                    </Link>
                )}
            </Menu>
        </Segment>
    );
};

export default CourseSidebarNav;
