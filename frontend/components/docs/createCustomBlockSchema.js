import { defaultBlockSpecs } from "@blocknote/core";
import AnalysisBlock from "./customBlocks/AnalysisBlock";
import TableChartBlock from "./customBlocks/TableChartBlock";

export const customBlockSchema = {
  ...defaultBlockSpecs,
  analysis: AnalysisBlock,
  "table-chart": TableChartBlock,
};
