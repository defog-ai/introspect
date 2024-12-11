import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewContent, NodeViewProps, NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import React, { useContext, useRef, useState } from "react";
import { OracleReportContext } from "../../context/OracleReportContext";
import { Drawer } from "antd";
import { OracleAnalysisFollowOn } from "./OracleAnalysisFollowOn";

interface RecommendationTitleAttrs {
  analysis_reference: string;
  idx: number;
}

const RecommendationTitleComponent = ({ node }: NodeViewProps) => {
  const { analyses } = useContext(OracleReportContext);
  const attrs = node.attrs as RecommendationTitleAttrs;
  const analysisReference = useRef(attrs.analysis_reference + "" || "");
  const recommendationIdx = useRef(attrs.idx);

  const analysisIds = useRef(analysisReference.current.split(","));

  const analysisParsed = useRef(
    analysisIds.current.map((id) => analyses[id]).filter((d) => d)
  );

  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <NodeViewWrapper className="react-component not-prose underline underline-offset-2 group">
      <p
        className="relative font-bold text-lg cursor-pointer"
        onClick={() => setDrawerOpen(true)}
      >
        <NodeViewContent />
        <span className="text-gray-400 text-sm font-light dark:text-gray-200">
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
        <OracleAnalysisFollowOn
          initialAnalyses={analysisParsed.current}
          recommendationIdx={recommendationIdx.current}
        />
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
        isRequired: true,
      },
      idx: {
        default: 100000,
        isRequired: true,
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
