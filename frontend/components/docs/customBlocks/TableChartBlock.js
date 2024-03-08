import { createReactBlockSpec } from "@blocknote/react";
import { TableChart } from "../../defog-components/components/TableChart";
import ErrorBoundary from "../../common/ErrorBoundary";

const TableChartBlock = createReactBlockSpec(
  {
    type: "table-chart",
    content: "none",
    propSchema: {
      id: {
        default: null,
      },
    },
  },
  {
    render: ({ block, editor }) => {
      // need block.props when drag and dropping.
      // if dropping, table id is in block.props.id, otherwise just use block.id
      return (
        <ErrorBoundary>
          <TableChart tableId={block.props.id || block.id}></TableChart>
        </ErrorBoundary>
      );
    },
  }
);

export default TableChartBlock;
