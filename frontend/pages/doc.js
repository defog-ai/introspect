import "@blocknote/react/style.css";
import React, { useContext, useEffect, useRef, useState } from "react";
import Meta from "../components/common/Meta";
import Scaffolding from "../components/common/Scaffolding";
import { useRouter } from "next/router";
import dynamic from "next/dynamic";
import ErrorBoundary from "../components/common/ErrorBoundary";
import LoadingReport from "../components/reports/ReportLoading";
import { v4 } from "uuid";
import { Context } from "../components/common/Context";

const Doc = dynamic(() => import("../components/docs/Doc"), {
  ssr: false,
});

export default function DocPage() {
  const router = useRouter();
  const [context, setContext] = useContext(Context);

  const [user, setUser] = useState(context.user);

  const apiToken = process.env.NEXT_PUBLIC_DEFOG_API_KEY;
  const docId = useRef(null);

  useEffect(() => {
    let token = context.token;
    let userType = context.userType;

    if (!userType) {
      // load from local storage and set context
      const user = localStorage.getItem("defogUser");
      setUser(user);
      token = localStorage.getItem("defogToken");
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
    if (!token) {
      router.push("/log-in");
    }

    docId.current = router?.query?.docId;
    // sometimes router.query can be empty for some reason
    // look in router.asPath
    if (!docId.current) {
      const asPath = router?.asPath;
      const docIdMatch = asPath.match(/doc\?docId=([^&]*)/);
      if (docIdMatch) {
        docId.current = docIdMatch[1];
      }
    }

    async function validate() {
      try {
        // create a new doc if id is new or undefined

        if (router && (docId.current === "new" || !docId.current)) {
          docId.current = v4();
          router.replace({
            query: {
              docId: docId.current,
            },
          });
        }
      } catch (e) {
        console.log(e);
      }
    }

    validate();
  }, [router, context, setContext]);

  return docId.current ? (
    <>
      <Meta />
      <Scaffolding id={"view-notebooks"} userType={"admin"}>
        <ErrorBoundary>
          <Doc docId={docId.current} username={user} apiToken={apiToken}></Doc>
        </ErrorBoundary>
      </Scaffolding>
    </>
  ) : (
    <LoadingReport title="Verifying your details..."></LoadingReport>
  );
}
