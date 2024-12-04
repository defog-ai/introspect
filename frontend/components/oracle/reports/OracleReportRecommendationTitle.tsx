import { mergeAttributes, Node } from "@tiptap/core";
import {
  EditorContent,
  EditorProvider,
  NodeViewWrapper,
  ReactNodeViewRenderer,
  useCurrentEditor,
} from "@tiptap/react";
import React, { useContext, useMemo, useRef } from "react";
import { OracleReportContext } from "../../context/OracleReportContext";
import { Drawer } from "antd";
import { extensions, parseTablesAndImagesInMdx } from "$utils/oracleUtils";

const RecommendationTitleComponent = ({ node }) => {
  const { analyses, analysesMdx } = useContext(OracleReportContext);
  const analysisReference = useRef(node.attrs.analysis_reference || "");

  const analysisIds = useRef(
    analysisReference.current.split(",").map((id) => parseInt(id.trim()))
  );

  const mdx = useRef(
    parseTablesAndImagesInMdx(
      analysisIds.current.map((id) => analysesMdx[id]).join("\n\n")
    )
  );

  console.log(mdx);

  const [drawerOpen, setDrawerOpen] = React.useState(false);

  return (
    <NodeViewWrapper className="react-component not-prose underline underline-offset-2 group">
      <p
        className="relative font-bold text-lg cursor-pointer"
        onClick={() => setDrawerOpen(true)}
      >
        {node.content.content?.[0]?.text || ""}
        <span className="absolute bottom-1 ml-1 text-right text-gray-400 italic text-xs font-light opacity-0 group-hover:opacity-100">
          Click for details
        </span>
      </p>
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        placement="left"
        size="large"
        title="Details"
      >
        <OracleReportContext.Provider
          value={{
            tables: mdx.current.tables,
            multiTables: mdx.current.multiTables,
            images: mdx.current.images,
          }}
        >
          <EditorProvider
            extensions={extensions}
            content={mdx.current.mdx}
            editable={false}
            editorProps={{
              attributes: {
                class:
                  "oracle-report-tiptap prose prose-base mx-auto p-2 mb-12 md:mb-0 focus:outline-none [&_.react-multitable-container]:lg:mx-0",
              },
            }}
          />
        </OracleReportContext.Provider>
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
        parseHTML: (element) => "" + element.getAttribute("analysis_reference"),
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
