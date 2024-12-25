import { mergeAttributes, Node } from "@tiptap/core";
import {
  NodeViewContent,
  NodeViewProps,
  NodeViewWrapper,
  ReactNodeViewRenderer,
} from "@tiptap/react";
import React, { useContext, useRef, useState, useEffect } from "react";
import { OracleReportContext } from "../../context/OracleReportContext";
import { OracleAnalysisFollowOn } from "./OracleAnalysisFollowOn";
import { Pencil, Delete } from "lucide-react"

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

  const markIrrelevant = () => {
    console.log('Marked as irrelevant');
  };

  const editAnalysis = () => {
    console.log('Edit analysis clicked');
  };

  return (
    <NodeViewWrapper className="react-component not-prose group">
      <div className="relative font-bold text-lg flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="cursor-pointer">
            <NodeViewContent />
          </div>
          <span 
            className="text-gray-400/60 hover:text-gray-600 hover:font-bold dark:text-gray-500/60 dark:hover:text-gray-300 cursor-pointer rounded-md transition-colors duration-200"
            onClick={editAnalysis}
            title="Edit this analysis"
          >
            <Pencil />
          </span>
          <span 
            className="text-gray-400/60 hover:text-gray-600 hover:font-bold dark:text-gray-500/60 dark:hover:text-gray-300 cursor-pointer rounded-md transition-colors duration-200"
            onClick={markIrrelevant}
            title="Mark this analysis as irrelevant"
          >
            <Delete />
          </span>
        </div>
        <div className="flex gap-4 text-sm font-light">
          <span 
            className="text-gray-600 dark:text-gray-300 cursor-pointer px-3 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200 underline hover:font-bold"
            onClick={() => setDrawerOpen(true)}
            title="View detailed analysis"
          >
            ✨ Dig Deeper
          </span>
        </div>
      </div>

      {/* Backdrop */}
      <div 
        className={`fixed inset-0 bg-black transition-opacity duration-300 ease-in-out ${drawerOpen ? 'bg-opacity-50 z-40' : 'bg-opacity-0 pointer-events-none -z-10'}`}
        onClick={() => setDrawerOpen(false)}
      />
      
      {/* Drawer */}
      <div 
        className={`fixed inset-y-0 left-0 w-[48rem] bg-white dark:bg-gray-800 shadow-xl transform transition-transform duration-300 ease-in-out ${
          drawerOpen ? 'translate-x-0 z-50' : '-translate-x-full -z-10'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900 dark:text-white">
                Dig Deeper
              </h2>
              <button
                onClick={() => setDrawerOpen(false)}
                className="p-1 rounded-md text-gray-400 hover:text-gray-500 focus:outline-none"
              >
                <span className="sr-only">Close panel</span>
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-4 py-6">
            <OracleAnalysisFollowOn
              initialAnalyses={analysisParsed.current}
              recommendationIdx={recommendationIdx.current}
            />
          </div>
        </div>
      </div>
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
