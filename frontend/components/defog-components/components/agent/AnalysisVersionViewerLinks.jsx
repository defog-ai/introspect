import React, { useEffect, useRef, useState } from "react";

export const AnalysisVersionViewerLinks = ({ analyses, activeAnalysisId }) => {
  const [paths, setPaths] = useState([]);
  // creates links bet
  const ctr = useRef(null);
  useEffect(() => {
    if (!ctr.current || !activeAnalysisId) return;

    const listCtr = ctr.current.closest(".history-list");
    if (!listCtr) return;

    // remove all "linked-active" classes
    listCtr.querySelectorAll(".linked-active").forEach((el) => {
      el.classList.remove("linked-active");
    });

    // remove all "current-active" classes
    listCtr.querySelectorAll(".current-active").forEach((el) => {
      el.classList.remove("current-active");
    });

    // now select the activeAnalysisId using classname, and add the "current-active" class
    const activeEl = listCtr.querySelector(`.${activeAnalysisId}`);
    if (activeEl) {
      activeEl.classList.add("current-active");
    }

    let currentAnalysis = analyses[activeAnalysisId];
    // now find all linkes
    const linked = [];
    const newPaths = [];
    while (linked.length < 20) {
      if (currentAnalysis.isRoot) {
        break;
      }
      // else look at directParentId
      const parentAnalysis = analyses[currentAnalysis.directParentId];
      linked.push(parentAnalysis);
      //   simultaneously create a path between currentAnalysis and parentAnalysis

      // render the links which are lines going from
      // left center of source, goes left 10 px
      // then goes to the down/up to the left center of the target
      // and then goes to the right 10px
      // the path should have rounded corners
      // just store the path in an array, and then render all paths at once
      //   note that these coords have to be relative to the listCtr

      const listCtrRect = listCtr.getBoundingClientRect();

      const currentAnalysisEl = listCtr.querySelector(
        `.${currentAnalysis.analysisId}`
      );
      const parentAnalysisEl = listCtr.querySelector(
        `.${parentAnalysis.analysisId}`
      );

      const currentAnalysisRect = currentAnalysisEl.getBoundingClientRect();
      const parentAnalysisRect = parentAnalysisEl.getBoundingClientRect();

      const currentAnalysisCenter = {
        x: currentAnalysisRect.left - listCtrRect.left - 12,
        y:
          currentAnalysisRect.top -
          listCtrRect.top +
          currentAnalysisRect.height / 2,
      };

      const parentAnalysisCenter = {
        x: parentAnalysisRect.left - listCtrRect.left - 12,
        y:
          parentAnalysisRect.top -
          listCtrRect.top +
          parentAnalysisRect.height / 2,
      };

      const deltaX1 = -10;
      const deltaY1 = 0;

      const deltaX2 = 0;
      const deltaY2 = parentAnalysisCenter.y - currentAnalysisCenter.y;

      const deltaX3 = parentAnalysisCenter.x - (currentAnalysisCenter.x - 10);
      const deltaY3 = 0;

      const path = `M ${currentAnalysisCenter.x} ${currentAnalysisCenter.y} l ${deltaX1} ${deltaY1} l ${deltaX2} ${deltaY2} l ${deltaX3} ${deltaY3}`;

      newPaths.push(path);

      currentAnalysis = parentAnalysis;
    }

    linked.forEach((analysis) => {
      const el = listCtr.querySelector(`.${analysis.analysisId}`);
      if (el) {
        el.classList.add("linked-active");
      }
    });

    setPaths(newPaths);
  }, [analyses, activeAnalysisId]);
  return (
    <div
      className="absolute l-0 t-0 pointer-events-none overflow-visible"
      ref={ctr}
    >
      <svg width="100%" height="100%" className="overflow-visible">
        {paths.map((path, index) => (
          <path
            key={index}
            d={path}
            className="fill-transparent stroke-blue-300 text-blue-500"
            strokeWidth="1"
          />
        ))}
      </svg>
    </div>
  );
};
