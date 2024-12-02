import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import { useContext, useMemo } from "react";
import { OracleReportContext } from "$components/context/OracleReportContext";
import { Table, Tabs } from "@defogdotai/agents-ui-components/core-ui";
import ErrorBoundary from "$components/layout/ErrorBoundary";
import { ChartContainer } from "@defogdotai/agents-ui-components/agent";

function OracleReportMultiTable(props) {
  const { multiTables, tables } = useContext(OracleReportContext);

  const { tableIds } = multiTables[props.node.attrs.id] || {};

  const tabs = useMemo(() => {
    // tabs within tabs
    const tableTabs = [];
    tableIds.forEach((tableId) => {
      const { columns, data } = tables[tableId] || {};
      tableTabs.push([
        {
          name: "Table",
          content: (
            <Table
              columns={columns}
              rows={data}
              columnHeaderClassNames="py-2"
              skipColumns={["index"]}
            />
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
      ]);
    });

    return tableTabs;
  }, [tables]);

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

export const OracleReportMultiTableExtension = Node.create({
  name: "oracle-multi-table",
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
        tag: "oracle-multi-table",
      },
    ];
  },
  renderHTML({ HTMLAttributes }) {
    return ["oracle-multi-table", mergeAttributes(HTMLAttributes)];
  },

  addNodeView() {
    return ReactNodeViewRenderer(OracleReportMultiTable);
  },
});
