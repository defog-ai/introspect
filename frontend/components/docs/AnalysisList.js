// a place to display various things avaialble to this user for the doc
// for example analyses, or other things
// expected they should be able to drag and drop these things into the doc

import React, { useContext, useEffect, useRef, useState } from "react";
import { DocContext } from "./DocContext";
import Search from "antd/es/input/Search";
import { Input } from "antd";
import ErrorBoundary from "../defog-components/components/common/ErrorBoundary";

export function AnalysisList() {
  const docContext = useContext(DocContext);
  const analysesRef = useRef(null);
  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    docContext.val.userItems.analyses
      .filter((d) => d && d.user_question)
      .map((analysis, i) => {
        let dom = analysesRef.current.querySelector(
          `#analysis-list-${analysis.report_id}`
        );

        dom.addEventListener("dragstart", (e) => {
          e.dataTransfer.clearData();
          e.dataTransfer.setData(
            "text/html",
            // all data-PROP_NAME attributes will go into the block.props.PROP_NAME. (make sure to define the propSchema in the block spec)
            // remember that attributes here are going to be lowercased and camelCased
            // so "analysis-id" becomes "analysisId"
            // your prop should be "analysisId"
            `<div data-content-type="analysis" data-analysis-id="${analysis.report_id}"></div>`
          );
        });
      });
  }, [docContext]);

  return (
    <ErrorBoundary>
      <div id="analysis-list-sidebar" ref={analysesRef} className="sidebar">
        <Input
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Filter your old analysis"
        />
        <div className="sidebar-content">
          {(docContext?.val?.userItems?.analyses || [])
            .filter((d) => d && d.user_question !== "")
            .filter((d) => d && d?.user_question?.includes(searchText))
            .map((analysis, i) => (
              <div
                draggable="true"
                key={analysis.report_id}
                id={`analysis-list-${analysis.report_id}`}
                className="analysis-list-sidebar-item"
              >
                <span>{analysis.user_question}</span>
              </div>
            ))}
        </div>
      </div>
    </ErrorBoundary>
  );
}
