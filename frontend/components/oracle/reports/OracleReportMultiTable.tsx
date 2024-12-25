import { mergeAttributes, Node } from "@tiptap/core";
import {
  NodeViewProps,
  NodeViewWrapper,
  ReactNodeViewRenderer,
} from "@tiptap/react";
import { useContext, useMemo, useState } from "react";
import { OracleReportContext } from "$components/context/OracleReportContext";
import { Table, Tabs } from "@defogdotai/agents-ui-components/core-ui";
import ErrorBoundary from "$components/layout/ErrorBoundary";
import { ChartContainer } from "@defogdotai/agents-ui-components/agent";
import { TABLE_TYPE_TO_NAME } from "$utils/oracleUtils";

interface OracleReportMultiTableProps {
  node: {
    attrs: {
      id: string;
    };
  };
}

function OracleReportMultiTable({ node }: NodeViewProps) {
  const { multiTables, tables } = useContext(OracleReportContext);

  const multiTableId = node.attrs.id as string;
  const multiTableEntry = multiTables[multiTableId];
  const tableIdList = Array.isArray(multiTableEntry?.tableIds)
    ? multiTableEntry.tableIds
    : [];

  const [selectedTableId, setSelectedTableId] = useState<string | null>(
    tableIdList.length > 0 ? tableIdList[0] : null
  );

  const tabs = useMemo(() => {
    // tabs within tabs
    const tableTabs: Record<string, any[]> = {};
    tableIdList.forEach((tableId) => {
      const { columns, data, attributes } = tables[tableId] || {};
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
                initialQuestion={attributes.generated_qn}
              />
            </ErrorBoundary>
          ),
        },
        attributes.sql
          ? {
              name: "SQL",
              content: (
                <pre className="whitespace-pre-wrap px-2 py-4 bg-gray-800">
                  <code>{attributes.sql}</code>
                </pre>
              ),
            }
          : null,
      ];
    });

    return tableTabs;
  }, [tables]);

  return (
    <NodeViewWrapper className="react-component react-multitable-container not-prose lg:-mx-40 my-10">
      {/* chips to select tables if there's more than one table */}
      {tableIdList && tableIdList.length > 1 && (
        <div className="table-selection flex flex-row gap-2 w-100 overflow-scroll mb-4">
          {tableIdList.map((id) => (
            <div
              className={`p-2 bg-gray-200 border border-gray-300 rounded-full cursor-pointer whitespace-nowrap text-xs ${
                selectedTableId === id
                  ? "bg-gray-600 border-transparent text-white"
                  : "text-gray-500 hover:bg-gray-300"
              }`}
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
          tabs={tabs[selectedTableId].filter(Boolean)}
          size="small"
          contentClassNames="border dark:border-gray-700"
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
        isRequired: true,
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
