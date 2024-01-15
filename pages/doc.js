import React, { useContext, useEffect, useRef, useState } from "react";
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

  const { user, token } = {
    user: "podcast-slot.0g@icloud.com",
    token: "dummy",
  };

  const apiToken = process.env.NEXT_PUBLIC_API_KEY;
  const docId = useRef(null);

  useEffect(() => {
    if (router && (!user || !token)) {
      router.push("/login");
      return;
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
  }, [router, context, token, user, setContext]);

  return docId.current ? (
    <ErrorBoundary>
      <Doc docId={docId.current} username={user} apiToken={apiToken}></Doc>
    </ErrorBoundary>
  ) : (
    <LoadingReport title="Verifying your details..."></LoadingReport>
  );
}
