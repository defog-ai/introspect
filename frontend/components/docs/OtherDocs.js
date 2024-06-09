import React, { Fragment, useEffect, useMemo, useState } from "react";
import { Dropdown } from "antd";
import { getAllDocs } from "$utils/utils";

export default function OtherDocs({ token, currentDocId }) {
  const [otherDocs, setOtherDocs] = useState([]);

  useEffect(() => {
    async function getDocs() {
      try {
        const json = await getAllDocs(token);
        if (json.success) {
          setOtherDocs(json.docs);
        }
      } catch (err) {
        console.log(err);
      }
    }
    getDocs();
  }, []);

  const items = useMemo(
    () =>
      otherDocs
        .filter((d) => d.doc_id !== currentDocId)
        .map((doc) => ({
          key: doc.doc_id,
          label: (
            <a href={"?docId=" + doc.doc_id} target="_blank" rel="noreferrer">
              <p>{doc.doc_title || "Untitled"}</p>
            </a>
          ),
        })),
    [otherDocs]
  );

  return (
    <>
      <Dropdown menu={{ items }} trigger={"click"}>
        <span>Open</span>
      </Dropdown>
    </>
  );
}
