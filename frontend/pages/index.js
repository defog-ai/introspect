import React, { useState, useEffect, useContext } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import { Spin } from "antd/lib";
import { UserContext } from "$components/context/UserContext";
import Scaffolding from "$components/layout/Scaffolding";

const QueryDatabase = () => {
  const [userType, setUserType] = useState("");
  const [context, setContext] = useContext(UserContext);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let userType = context.userType;
    if (!userType) {
      // load from local storage and set context
      const user = localStorage.getItem("defogUser");
      const token = localStorage.getItem("defogToken");
      userType = localStorage.getItem("defogUserType");

      if (!user || !token || !userType) {
        // redirect to login page
        router.push("/log-in");
        return;
      }
      setContext({
        user: user,
        token: token,
        userType: userType,
      });
    }
    setUserType(userType);
    setLoading(false);
    if (userType === "admin") {
      console.log("redirecting to extract metadata..");
      router.push("/extract-metadata");
    } else {
      console.log("redirecting to view notebooks..");
      router.push("/view-notebooks");
    }
  }, []);

  return (
    <>
      <Meta />
      <Scaffolding userType={userType}>
        <h1 style={{ paddingBottom: "1em" }}>Welcome to Defog!</h1>
        <h3>
          Please wait while we log you in and redirect you to the right page...{" "}
          <Spin />
        </h3>
      </Scaffolding>
    </>
  );
};

export default QueryDatabase;
