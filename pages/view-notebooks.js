import React, { useState, useContext, useEffect, useRef } from "react";
import DocIcon from "../components/docs/DocIcon";
import styled from "styled-components";
import { Context } from "../components/common/Context";
import Meta from "../components/common/Meta";
import { message } from "antd";
import Link from "next/link";
import Scaffolding from "../components/common/Scaffolding";

const ViewNotebooks = () => {
  const [loading, setLoading] = useState(false);
  const [context, setContext] = useContext(Context);
  const [ownDocs, setOwnDocs] = useState([]);
  const [recentlyViewed, setRecentlyViewed] = useState([]);

  const getNotebooks = async () => {
    if (!context.token) {
      return;
    }

    let res = await fetch(`http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/get_docs`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        api_key: context.token,
      }),
    });
    res = await res.json();
    if (res.success) {
      // res.docs is user's own documents
      const filteredDocs = res.docs;
      // res.recently_viewed_docs is user's recently viewed documents
      let recentlyViewed = res.recently_viewed_docs || [];

      filteredDocs.forEach((r) => {
        r.timestamp = new Date(r.timestamp);
      });

      recentlyViewed = recentlyViewed.map((r) => {
        return {
          ...r,
          timestamp: new Date(r.timestamp),
          created_by: r.username === context.user ? "You" : r.username,
        };
      });

      filteredDocs.sort((a, b) => {
        return b.timestamp - a.timestamp;
      });

      setRecentlyViewed(recentlyViewed);

      recentlyViewed.sort((a, b) => {
        return b.timestamp - a.timestamp;
      });

      setOwnDocs(filteredDocs);
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
        router.push("/login");
        return;
      }
      setContext({
        user: user,
        token: token,
        userType: userType,
      });
    }
    if (!token) {
      router.push("/login");
    } else {
      getNotebooks();
    }
  }, [context, context.token]);

  return (
    <>
      <Meta/>
      <Scaffolding id={"view-notebooks"} userType={context.userType}>
        <h1>View Notebooks</h1>
        {recentlyViewed.length ? <h2 className="header">Recently viewed</h2> : null}
        <div className="doc-icons-container">
          {recentlyViewed && !loading ? (
            <>
              {recentlyViewed.map((doc) => (
                <Link
                  target="_blank"
                  href={{
                    pathname: "/doc",
                    query: { docId: doc.doc_id },
                  }}
                  key={doc.doc_id}
                >
                  <DocIcon doc={doc} recentlyViewed={true} />
                </Link>
              ))}
            </>
          ) : (
            <div>Loading recently viewed docs...</div>
          )}
        </div>

        <h2 className="header">Your documents</h2>
        <div className="doc-icons-container">
          {ownDocs && !loading ? (
            <>
              <Link
                target="_blank"
                href={{
                  pathname: "/doc",
                  query: { docId: "new" },
                }}
              >
                <DocIcon addDocIcon={true} />
              </Link>
              {ownDocs.map((doc) => (
                <Link
                  target="_blank"
                  href={{
                    pathname: "/doc",
                    query: { docId: doc.doc_id },
                  }}
                  key={doc.doc_id}
                >
                  <DocIcon doc={doc} />
                </Link>
              ))}
            </>
          ) : (
            <div>Loading docs...</div>
          )}
        </div>
      </Scaffolding>
    </>
  )
}

export default ViewNotebooks;