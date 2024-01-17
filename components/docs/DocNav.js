import React, { Fragment, useEffect, useState } from "react";
import OtherDocs from "./OtherDocs";
import { GrNewWindow } from "react-icons/gr";

const sidebarWidth = 170;

export default function DocNav({ apiToken, username, currentDocId }) {
  const [sidebarsOpen, setSidebarsOpen] = useState({
    "analysis-list-sidebar": false,
    "db-creds-sidebar": false,
  });

  useEffect(() => {
    let ctr = document.getElementById("doc-sidebars");

    if (!ctr) return;

    let count = 0;

    // if nothing is true, close the ctr
    if (
      sidebarsOpen["analysis-list-sidebar"] ||
      sidebarsOpen["db-creds-sidebar"]
    ) {
      ctr.classList.add("open");
    } else {
      ctr.classList.remove("open");
    }

    for (let sidebar in sidebarsOpen) {
      let el = document.getElementById(sidebar);
      if (!el) return;
      if (sidebarsOpen[sidebar]) {
        el.classList.add("open");
        count++;
      } else {
        el.classList.remove("open");
      }
    }
    // ctr.style.minWidth = `${count * sidebarWidth + 20}px`;
  }, [sidebarsOpen]);

  function toggleSidebar(sidebarNm) {
    setSidebarsOpen((prev) => {
      return {
        ...prev,
        [sidebarNm]: !prev[sidebarNm],
      };
    });
  }

  return (
    <>
      <div id="editor-nav">
        {/* new doc button */}
        <div id="nav-new-doc">
          <a href={"?docId=new"} target="_blank">
            <div title="Start a new doc">
              <span>New</span>
              <GrNewWindow />
            </div>
          </a>
        </div>

        {/* other docs */}
        <div id="nav-other-docs" title="List of other docs of this user">
          <OtherDocs
            apiToken={apiToken}
            username={username}
            currentDocId={currentDocId}
          ></OtherDocs>
        </div>

        <div className="nav-spacer"></div>
        {/* eveything after this spacer is on the right of the nav */}

        <div
          id="nav-db-creds"
          className={
            "nav-sidebar-btn-stick-right " +
            (sidebarsOpen["db-creds-sidebar"] ? "" : "closed")
          }
          title="List of other docs of this user"
          onClick={(e) => {
            e.preventDefault();

            toggleSidebar("db-creds-sidebar");
          }}
        >
          DB creds
        </div>
        <div
          id="nav-analyses"
          className={
            "nav-sidebar-btn-stick-right " +
            (sidebarsOpen["analysis-list-sidebar"] ? "" : "closed")
          }
          title="List of other docs of this user"
          onClick={(e) => {
            e.preventDefault();

            toggleSidebar("analysis-list-sidebar");
          }}
        >
          Past analyses
        </div>
      </div>
    </>
  );
}
