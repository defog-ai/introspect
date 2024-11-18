import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import { useContext, useMemo } from "react";
import { OracleReportContext } from "$components/context/OracleReportContext";
import { Table, Tabs } from "@defogdotai/agents-ui-components/core-ui";
import ErrorBoundary from "$components/layout/ErrorBoundary";
import { ChartContainer } from "@defogdotai/agents-ui-components/agent";

function OracleReportTable(props) {
  const { tables } = useContext(OracleReportContext);

  const { data, columns } = tables[props.node.attrs.id] || {};

  const tabs = useMemo(() => {
    return [
      {
        name: "Table",
        content: (
          <Table columns={columns} rows={data} columnHeaderClassNames="py-2" skipColumns={["index"]} />
        ),
      },
      {
        name: "Chart",
        content: (
          <ErrorBoundary>
            <ChartContainer
              rows={data}
              columns={columns}
              initialQuestion={""}
            />
          </ErrorBoundary>
        ),
      },
    ];
  }, [tables, data, columns]);

  return (
    <NodeViewWrapper className="react-component not-prose">
      <Tabs
        // @ts-ignore
        tabs={tabs}
        size="small"
        rootClassNames="lg:-mx-40 my-10"
        contentClassNames="border"
      />
    </NodeViewWrapper>
  );
}

export const OracleReportTableExtension = Node.create({
  name: "oracle-table",
  group: "block",

  addAttributes() {
    return {
      id: {
        default: null,
      },
    };
  },
  parseHTML() {
    return [
      {
        tag: "oracle-table",
      },
    ];
  },
  renderHTML({ HTMLAttributes }) {
    return ["oracle-table", mergeAttributes(HTMLAttributes)];
  },

  addNodeView() {
    return ReactNodeViewRenderer(OracleReportTable);
  },
});
