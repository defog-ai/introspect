import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import { useContext, useMemo, useState } from "react";
import { OracleReportContext } from "$components/context/OracleReportContext";
import { Table, Tabs } from "@defogdotai/agents-ui-components/core-ui";
import ErrorBoundary from "$components/layout/ErrorBoundary";
import { ChartContainer } from "@defogdotai/agents-ui-components/agent";

function OracleReportMultiTable(props) {
  const { multiTables, tables } = useContext(OracleReportContext);

  const { tableIds } = multiTables[props.node.attrs.id] || { tableIds: [] };

  const [selectedTableId, setSelectedTableId] = useState(
    tableIds.length ? tableIds[0] : null
  );

  console.log(multiTables, tables);

  const tabs = useMemo(() => {
    // tabs within tabs
    const tableTabs = {};
    tableIds.forEach((tableId) => {
      const { columns, data } = tables[tableId] || {};
      tableTabs[tableId] = [
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
      ];
    });

    return tableTabs;
  }, [tables]);

  return (
    <NodeViewWrapper className="react-component not-prose">
      {/* chips to select tables if there's more than one table */}
      <div className="table-selection w-100 overflow-scroll">
        {tableIds.map((id) => (
          <div
            className={`px-2 py-1 bg-gray-300 text-gray-400 ${selectedTableId === id ? "bg-gray-300 text-white" : ""}`}
            key={id}
          >
            {id}
          </div>
        ))}
      </div>
      {tabs[selectedTableId] && (
        <Tabs
          // @ts-ignore
          tabs={tabs}
          size="small"
          rootClassNames="lg:-mx-40 my-10"
          contentClassNames="border"
          defaultSelected={selectedTableId}
        />
      )}
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
