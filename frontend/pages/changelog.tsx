import React from "react";
import Head from "next/head";
import Home from "../components/Home/Home";
import Changelog from "../components/Changelog";

const LandingPage = () => {
    return (
        <>
            <Head>
                <title>OHQ | Changelog</title>
            </Head>
            <Home>
                <Changelog />
            </Home>
        </>
    );
};

export default LandingPage;
