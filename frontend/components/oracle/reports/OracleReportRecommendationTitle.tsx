import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import React, { useContext, useMemo, useRef, useState } from "react";
import { OracleReportContext } from "../../context/OracleReportContext";
import { Drawer } from "antd";
import { extensions, parseMDX } from "$utils/oracleUtils";
import { OracleAnalysisFollowOn } from "./OracleAnalysisFollowOn";

const RecommendationTitleComponent = ({ node }) => {
  const { analyses } = useContext(OracleReportContext);
  const analysisReference = useRef(node.attrs.analysis_reference + "" || "");

  const analysisIds = useRef(
    analysisReference.current.split(",").map((id) => parseInt(id.trim()))
  );

  const analysisParsed = useRef(analysisIds.current.map((id) => analyses[id]));

  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <NodeViewWrapper className="react-component not-prose underline underline-offset-2 group">
      <p
        className="relative font-bold text-lg cursor-pointer"
        onClick={() => setDrawerOpen(true)}
      >
        {node.content.content?.[0]?.text || ""}
        <span className="absolute bottom-1 ml-1 text-right text-gray-400 text-sm font-light">
          ✨ Dig Deeper
        </span>
      </p>
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        placement="left"
        size="large"
        title="Details"
      >
        <OracleAnalysisFollowOn initialAnalyses={analysisParsed.current} />
      </Drawer>
    </NodeViewWrapper>
  );
};

export const RecommendationTitle = Node.create({
  name: "recommendationTitle",
  group: "block",
  content: "text*",
  addAttributes() {
    return {
      analysis_reference: {
        default: "",
      },
    };
  },
  parseHTML() {
    return [
      {
        tag: "oracle-recommendation-title",
      },
    ];
  },
  renderHTML({ HTMLAttributes }) {
    return ["oracle-recommendation-title", mergeAttributes(HTMLAttributes), 0];
  },
  addNodeView() {
    return ReactNodeViewRenderer(RecommendationTitleComponent);
  },
});
