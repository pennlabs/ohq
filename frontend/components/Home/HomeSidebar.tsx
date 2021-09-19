import React, { useState } from "react";

import { Segment, Menu, Grid, Image } from "semantic-ui-react";
import Link from "next/link";

import { useRouter } from "next/router";
import SignOutButton from "../SignOut";
import styles from "../../styles/landingpage.module.css";
import AboutModal from "../common/AboutModal";

const Sidebar = () => {
    const router = useRouter();
    const [showAboutModal, setShowAboutModal] = useState(false);

    return (
        <Grid.Column width={3}>
            <Segment basic>
                <Link href="/" as="/">
                    <Image
                        src="../../../ohq.png"
                        size="tiny"
                        style={{ marginTop: "10px", cursor: "pointer" }}
                    />
                </Link>
                <Menu vertical secondary fluid>
                    <Link href="/" as="/">
                        <Menu.Item
                            style={{
                                whiteSpace: "nowrap",
                                textOverflow: "ellipsis",
                                overflow: "hidden",
                            }}
                            name="Dashboard"
                            icon="dashboard"
                            active={router.pathname === "/"}
                            color="blue"
                        />
                    </Link>
                    <Link href="/settings" as="/settings">
                        <Menu.Item
                            style={{
                                whiteSpace: "nowrap",
                                textOverflow: "ellipsis",
                                overflow: "hidden",
                            }}
                            name="Account Settings"
                            icon="setting"
                            active={router.pathname === "/settings"}
                            color="blue"
                        />
                    </Link>
                    <Link href="/changelog" as="/changelog">
                        <Menu.Item
                            style={{
                                whiteSpace: "nowrap",
                                textOverflow: "ellipsis",
                                overflow: "hidden",
                            }}
                            name="Change Log"
                            icon="file text"
                            active={router.pathname === "/changelog"}
                            color="blue"
                        />
                    </Link>
                    <Link href="/faq" as="/faq">
                        <Menu.Item
                            style={{
                                whiteSpace: "nowrap",
                                textOverflow: "ellipsis",
                                overflow: "hidden",
                            }}
                            name="FAQ"
                            icon="question circle"
                            active={router.pathname === "/faq"}
                            color="blue"
                        />
                    </Link>
                    <SignOutButton />
                </Menu>
            </Segment>
            <div
                role="button"
                className={`${styles.about} ${styles["about-dashboard"]}`}
            >
                <a
                    href="https://airtable.com/shrIZxIjyAE3gOUSg"
                    target="_blank"
                    rel="noreferrer"
                >
                    <p>Feedback</p>
                </a>
            </div>
            <AboutModal
                open={showAboutModal}
                closeFunc={() => setShowAboutModal(false)}
            />
        </Grid.Column>
    );
};

export default Sidebar;
