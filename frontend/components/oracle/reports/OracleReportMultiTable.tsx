import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import { useContext, useMemo, useState } from "react";
import { OracleReportContext } from "$components/context/OracleReportContext";
import { Table, Tabs } from "@defogdotai/agents-ui-components/core-ui";
import ErrorBoundary from "$components/layout/ErrorBoundary";
import { ChartContainer } from "@defogdotai/agents-ui-components/agent";
import { TABLE_TYPE_TO_NAME } from "$utils/oracleUtils";

function OracleReportMultiTable(props) {
  const { multiTables, tables } = useContext(OracleReportContext);

  const { tableIds } = multiTables[props.node.attrs.id] || { tableIds: [] };

  const [selectedTableId, setSelectedTableId] = useState(
    tableIds.length ? tableIds[0] : null
  );

  console.log(tables);

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
    <NodeViewWrapper className="react-component not-prose lg:-mx-40 my-10">
      {/* chips to select tables if there's more than one table */}
      {tableIds && tableIds.length > 0 && (
        <div className="table-selection flex flex-row gap-2 w-100 overflow-scroll mb-4">
          {tableIds.map((id) => (
            <div
              className={`p-2 bg-gray-200 border border-gray-300 rounded-full cursor-pointer whitespace-nowrap text-xs ${selectedTableId === id ? "bg-gray-600 border-transparent text-white" : "text-gray-500 hover:bg-gray-300"}`}
              key={id}
              onClick={() => setSelectedTableId(id)}
            >
              {TABLE_TYPE_TO_NAME[tables[id]?.type] ||
                tables[id]?.type ||
                "Table"}
            </div>
          ))}
        </div>
      )}

      {tabs[selectedTableId] && (
        <Tabs
          // @ts-ignore
          tabs={tabs[selectedTableId]}
          size="small"
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
