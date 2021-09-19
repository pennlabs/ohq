import React, { useContext, useState, useEffect } from "react";
import { Grid, Header, Segment, Message, Label } from "semantic-ui-react";
import Alert from "@material-ui/lab/Alert";
import Snackbar from "@material-ui/core/Snackbar";
import InstructorCourses from "./InstructorCourses";
import StudentCourses from "./StudentCourses";
import Footer from "../../common/Footer";
import { AuthUserContext } from "../../../context/auth";
import { Kind, UserMembership } from "../../../types";
import { useMemberships } from "../../../hooks/data-fetching/dashboard";
import { isLeadershipRole } from "../../../utils/enums";
import { FALL_2021_TRANSITION_MESSAGE_TOKEN } from "../../../constants";
import ModalShowNewChanges from "./Modals/ModalShowNewChanges";

// TODO: try to readd new user stuff, rip out loading stuff
const Dashboard = () => {
    const { user: initialUser } = useContext(AuthUserContext);
    if (initialUser === undefined) {
        throw new Error("Must be logged-in");
    }
    const [messageDisp, setMessageDisp] = useState(false);
    useEffect(() => {
        const state = localStorage.getItem(FALL_2021_TRANSITION_MESSAGE_TOKEN);
        setMessageDisp(state !== "true");
    }, []);

    const { memberships, mutate } = useMemberships(initialUser);

    const getMemberships = (isStudent: boolean): UserMembership[] => {
        return memberships.filter((membership) => {
            return (
                (isStudent && membership.kind === Kind.STUDENT) ||
                (!isStudent && membership.kind !== Kind.STUDENT)
            );
        });
    };

    const isFaculty = initialUser.groups.includes("platform_faculty");

    const canCreateCourse: boolean =
        memberships.findIndex((membership) =>
            isLeadershipRole(membership.kind)
        ) !== -1 || isFaculty;

    /* STATE */
    // const [newUserModalOpen, setNewUserModalOpen] = useState(props.newUser);
    const showInstructorCourses =
        getMemberships(false).length > 0 || canCreateCourse;
    const [toast] = useState({ message: "", success: true });
    const [toastOpen, setToastOpen] = useState(false);

    const [logToast] = useState({
        message: "View new changes to OHQ.io",
        success: true,
    });
    const [logOpen, setLogOpen] = useState(false);
    const [logModal, setLogModal] = useState(false);

    useEffect(() => {
        Promise.all([
            fetch("./changelog.md").then((md) => md.text()),
            `${window.localStorage.getItem("changelogsaved")}`,
        ]).then(([updatedMd, savedMd]) => {
            if (updatedMd !== savedMd) setLogOpen(true);
        });
    }, []);

    return (
        <Grid.Column
            width={13}
            style={{ display: "flex", flexDirection: "column" }}
        >
            {memberships && (
                <Grid padded stackable>
                    <Grid.Row>
                        <Segment basic padded>
                            <Header as="h2">
                                <Header.Content>Student Courses</Header.Content>
                            </Header>
                        </Segment>
                        {messageDisp && (
                            <div
                                style={{
                                    position: "absolute",
                                    left: "50%",
                                    transform: "translateX(-50%)",
                                }}
                            >
                                <Message
                                    onDismiss={() => {
                                        setMessageDisp(false);
                                        localStorage.setItem(
                                            FALL_2021_TRANSITION_MESSAGE_TOKEN,
                                            "true"
                                        );
                                    }}
                                    size="mini"
                                    header="Welcome back!"
                                    content={
                                        <>
                                            Spring and Summer 2021 courses have
                                            been archived in preparation for
                                            Fall 2021.
                                            <br />
                                            Please contact us at contact@ohq.io
                                            if this is an error.
                                        </>
                                    }
                                />
                            </div>
                        )}
                    </Grid.Row>
                    <StudentCourses
                        memberships={getMemberships(true)}
                        mutate={mutate}
                    />
                    {showInstructorCourses && (
                        <>
                            <Grid.Row>
                                <Segment basic padded>
                                    <Header as="h2">
                                        <Header.Content>
                                            Instructor Courses
                                        </Header.Content>
                                    </Header>
                                </Segment>
                            </Grid.Row>
                            <InstructorCourses
                                memberships={getMemberships(false)}
                                mutate={mutate}
                                canCreateCourse={canCreateCourse}
                            />
                        </>
                    )}
                </Grid>
            )}
            <Snackbar
                open={toastOpen}
                autoHideDuration={6000}
                onClose={() => setToastOpen(false)}
            >
                <Alert
                    severity={toast.success ? "success" : "error"}
                    onClose={() => setToastOpen(false)}
                >
                    {toast.message}
                </Alert>
            </Snackbar>

            <Snackbar
                open={logOpen}
                autoHideDuration={6000}
                onClose={() => setLogOpen(false)}
            >
                <Alert severity="info" onClose={() => setLogOpen(false)}>
                    <Label
                        style={{ cursor: "pointer" }}
                        color="blue"
                        onClick={() => {
                            setLogOpen(false);
                            setLogModal(true);
                        }}
                    >
                        {logToast.message}
                    </Label>
                </Alert>
            </Snackbar>

            <Footer />
            <ModalShowNewChanges openModal={logModal} setOpen={setLogModal} />
        </Grid.Column>
    );
};

export default Dashboard;
