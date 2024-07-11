import React, { useState, useContext, useEffect, useRef } from "react";
import { DocIcon } from "$agents-ui-components";
import Meta from "$components/layout/Meta";
import { Collapse, message } from "antd";
import { useRouter } from "next/router";
import setupBaseUrl from "$utils/setupBaseUrl";
import Scaffolding from "$components/layout/Scaffolding";
import { UserContext } from "$components/context/UserContext";

const ViewNotebooks = () => {
  const [loading, setLoading] = useState(false);
  const [context, setContext] = useContext(UserContext);
  const [ownDocs, setOwnDocs] = useState([]);
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const [archivedDocs, setArchivedDocs] = useState([]);

  const router = useRouter();

  async function archiveToggle(doc) {
    const docId = doc.doc_id;
    const isArchived = doc.archived;
    // toggle archived status of doc
    let newArchivedDocs = archivedDocs;
    let newOwnDocs = ownDocs;

    if (isArchived) {
      // if doc is archived, remove from archived docs
      newArchivedDocs = archivedDocs.filter((doc) => doc.doc_id !== docId);
      // add to own docs
      newOwnDocs = [
        ...ownDocs,
        ...archivedDocs
          .filter((doc) => doc.doc_id === docId)
          .map((doc) => {
            doc.archived = false;
            return doc;
          }),
      ];
    } else {
      // if doc is not archived, add to archived docs
      newArchivedDocs = [
        ...archivedDocs,
        ...ownDocs
          .filter((doc) => doc.doc_id === docId)
          .map((doc) => {
            doc.archived = true;
            return doc;
          }),
      ];
      // remove from own docs
      newOwnDocs = ownDocs.filter((doc) => doc.doc_id !== docId);
    }

    setArchivedDocs(newArchivedDocs);
    setOwnDocs(newOwnDocs);

    // send to backend to the toggle_archive_status/ endpoint with the archive_status key
    let res = await fetch(setupBaseUrl("http", "toggle_archive_status"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        doc_id: docId,
        archive_status: !isArchived,
      }),
    });
    res = await res.json();
    if (res.success) {
      message.success(`Successfully ${isArchived ? "un" : ""}archived doc`);
    }
    if (!res.success) {
      message.error(`Error ${isArchived ? "un" : ""}archiving doc`);
    }
  }

  const getNotebooks = async () => {
    if (!context.token) {
      return;
    }

    let res = await fetch(setupBaseUrl("http", "get_docs"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token: context.token,
      }),
    });
    res = await res.json();
    if (res.success) {
      // res.docs is user's own documents
      let ownDocs = res.docs;
      // res.recently_viewed_docs is user's recently viewed documents
      let recentlyViewed = res.recently_viewed_docs || [];

      ownDocs.forEach((r) => {
        r.timestamp = new Date(r.timestamp);
      });

      recentlyViewed = recentlyViewed.map((r) => {
        return {
          ...r,
          timestamp: new Date(r.timestamp),
          created_by: r.username === context.user ? "You" : r.username,
        };
      });

      ownDocs.sort((a, b) => {
        return b.timestamp - a.timestamp;
      });

      setRecentlyViewed(recentlyViewed);

      recentlyViewed.sort((a, b) => {
        return b.timestamp - a.timestamp;
      });

      // res.archived_docs is user's archived documents
      const archivedDocs = ownDocs.filter((doc) => doc.archived);
      // remove archived docs from ownDocs
      ownDocs = ownDocs.filter((doc) => !doc.archived);
      setArchivedDocs(archivedDocs);

      setOwnDocs(ownDocs);
    }
    if (!res.success) {
      throw new Error(res.error_message);
    }
    setLoading(false);
  };

  useEffect(() => {
    setLoading(true);
    let token = context.token;
    let userType = context.userType;
    if (!userType) {
      // load from local storage and set context
      const user = localStorage.getItem("defogUser");
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
    } else {
      getNotebooks();
    }
  }, [context, context.token]);

  return (
    <>
      <Meta />
      <Scaffolding id={"view-notebooks"} userType={context.userType}>
        <h1 className="text-2xl font-bold mb-4">Notebooks</h1>

        <h2 className="text-lg mb-4">Your notebooks</h2>
        <div className="flex flex-wrap justify-start">
          {ownDocs && !loading ? (
            <>
              <DocIcon addDocIcon={true} />
              {ownDocs.map((doc) => (
                <DocIcon doc={doc} key={doc.doc_id} onClick={archiveToggle} />
              ))}
            </>
          ) : (
            <div>Loading docs...</div>
          )}
        </div>

        {recentlyViewed.length ? (
          <h2 className="text-lg mb-4">Recently viewed</h2>
        ) : null}
        <div className="flex flex-wrap justify-start">
          {recentlyViewed && !loading ? (
            <>
              {recentlyViewed.map((doc) => (
                <DocIcon
                  key={doc.doc_id}
                  doc={doc}
                  onClick={archiveToggle}
                  recentlyViewed={true}
                />
              ))}
            </>
          ) : (
            <div>Loading recently viewed docs...</div>
          )}
        </div>

        {archivedDocs.length === 0 ? (
          <></>
        ) : (
          <>
            <Collapse
              bordered={false}
              size="small"
              rootClassName="archived-collapse"
              items={[
                {
                  label: "Archived notebooks",
                  key: "archived-docs",
                  children: (
                    <div className="doc-icons-container">
                      {archivedDocs.map((doc) => (
                        <DocIcon
                          doc={doc}
                          onClick={archiveToggle}
                          key={doc.doc_id}
                        />
                      ))}
                    </div>
                  ),
                },
              ]}
            />
          </>
        )}
      </Scaffolding>
    </>
  );
};

export default ViewNotebooks;
