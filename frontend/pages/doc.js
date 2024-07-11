import "@blocknote/react/style.css";
import React, { useContext, useEffect, useRef, useState } from "react";
import Meta from "$components/layout/Meta";
import { useRouter } from "next/router";
import dynamic from "next/dynamic";
import ErrorBoundary from "$components/layout/ErrorBoundary";
import { v4 } from "uuid";
import { UserContext } from "$components/context/UserContext";
import Scaffolding from "$components/layout/Scaffolding";
// import { Doc } from "$agents-ui-components";

const Doc = dynamic(
  () =>
    import("$agents-ui-components").then((module) => {
      return module.Doc;
    }),
  {
    ssr: false,
  }
);

export default function DocPage() {
  const router = useRouter();
  const [context, setContext] = useContext(UserContext);

  const [user, setUser] = useState(context.user);
  const token = context.token;
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

  console.log(docId.current, token);

  return docId.current ? (
    <>
      <Meta />
      <Scaffolding id={"view-notebooks"} userType={"admin"}>
        <ErrorBoundary>
          <Doc docId={docId.current} user={user} token={token}></Doc>
        </ErrorBoundary>
      </Scaffolding>
    </>
  ) : (
    <h5>Verifying your details...</h5>
  );
}
