import React, { useState, Fragment, useContext, useEffect } from "react";
import { RelatedAnalysesContext } from "../../../docs/DocContext";
import { line, scaleLinear } from "d3";

export function RelatedAnalysesMiniMap({ editor = null }) {
  const relatedAnalysesContext = useContext(RelatedAnalysesContext);
  const pathGenerator = line()
    .x((d) => d.x)
    .y((d) => d.y);

  if (!relatedAnalysesContext) return null;

  // the document might keep shifting as new things are rendered, so calculate this stuff every, 1 second?
  const [svgPaths, setSvgPaths] = useState([]);

  useEffect(() => {
    const interval = setInterval(() => {
      const coords = Object.keys(relatedAnalysesContext.val).reduce(
        (acc, analysisId) => {
          // find where the block is in the document using data-analysis-id
          const block = document.querySelector(
            `[data-analysis-id="${analysisId}"]`
          );

          if (!block) return acc;

          // get coords relative to document, not scroll position
          const rect = block.getBoundingClientRect();
          const x = rect.x;
          const width = rect.width;
          const height = rect.height;
          const y = rect.y + window.scrollY;

          acc[analysisId] = { x, y, width, height };
          return acc;
        },
        {}
      );

      //   go through all the analyses, find all their follow_up_analyses, and make a path of width 10px between them
      //   if the parent analysis is not in the document, don't make a path

      const paths = Object.keys(relatedAnalysesContext.val).reduce(
        (acc, analysisId) => {
          const analysis = relatedAnalysesContext.val[analysisId];
          const { follow_up_analyses } = analysis;
          if (!follow_up_analyses || !follow_up_analyses.length) return acc;

          const parentCoords = coords[analysisId];
          if (!parentCoords) return acc;

          const parentX = parentCoords.x - 10;
          const parentY = parentCoords.y + parentCoords.height / 2;
          // starts from parentX - 1, parentY
          // goes left 10px
          // goes down to followUpX - 1, followUpY
          // goes right 10px

          const followUpPaths = follow_up_analyses.reduce(
            (acc2, followUpAnalysisId) => {
              const followUpCoords = coords[followUpAnalysisId];
              if (!followUpCoords) return acc2;
              const followUpX = followUpCoords.x - 10;
              const followUpY = followUpCoords.y - 20;

              const path = pathGenerator([
                { x: parentX - 1, y: parentY },
                { x: parentX - 11, y: parentY },
                { x: parentX - 11, y: followUpY },
                { x: followUpX - 1, y: followUpY },
              ]);
              return [...acc2, path];
            },
            []
          );

          return [...acc, ...followUpPaths];
        },
        []
      );

      setSvgPaths(paths);
    }, 1000);

    return () => clearInterval(interval);
  });

  //   using those coords, create svg paths that span the entire height of the document
  return (
    <div className="related-analyses-minimap">
      <svg width="100%" height="100%">
        {svgPaths.map((d, i) => {
          return <path d={d} stroke="black" strokeWidth="1px" key={i} />;
        })}
      </svg>
    </div>
  );
}
