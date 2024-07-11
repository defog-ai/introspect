import React, { Fragment, useEffect, useState } from "react";
import OtherDocs from "./OtherDocs";
import { Modal, message } from "antd";
import { deleteDoc } from "$utils/utils";
import { useRouter } from "next/router";
import TrashIcon from "$components/icons/TrashIcon";
import { PlusIcon } from "@heroicons/react/20/solid";

const sidebarWidth = 170;

export default function DocNav({ token, currentDocId }) {
  const [sidebarsOpen, setSidebarsOpen] = useState({
    "analysis-list-sidebar": false,
    "db-creds-sidebar": false,
  });

  const router = useRouter();

  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const showModal = (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    setIsDeleteModalOpen(true);
  };

  const handleDelete = async (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    const res = await deleteDoc(currentDocId);

    if (res.success) {
      message.success("Doc deleted successfully. Redirecting to home page...");

      setTimeout(() => {
        router.push("/view-notebooks");
      }, 1500);
    } else {
      message.error("Error deleting doc: " + (res.error_message || ""));
    }
    setIsDeleteModalOpen(false);
  };

  const handleCancel = (ev) => {
    // prevent trigger on the delete button
    ev.preventDefault();
    ev.stopPropagation();
    setIsDeleteModalOpen(false);
  };

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
          <a href={"?docId=new"} target="_blank" rel="noreferrer">
            <div title="Start a new doc">
              <span>New</span>
              <div>
                <PlusIcon className="w-3 h-3" />
              </div>
            </div>
          </a>
        </div>

        {/* other docs */}
        <div id="nav-other-docs" title="List of other docs of this user">
          <OtherDocs token={token} currentDocId={currentDocId}></OtherDocs>
        </div>

        {/* delete this doc */}
        <div id="nav-delete-doc" title="Delete this doc" onClick={showModal}>
          <span>Delete</span>
          <div>
            <TrashIcon className="h-3 w-3" />
          </div>
          <Modal
            okText={"Yes, delete"}
            okType="danger"
            title="Are you sure?"
            open={isDeleteModalOpen}
            onOk={handleDelete}
            onCancel={handleCancel}
          ></Modal>
        </div>

        <div className="nav-spacer"></div>
        {/* eveything after this spacer is on the right of the nav */}

        {/* <div
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
        </div> */}
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
