import { BlockNoteSchema, defaultBlockSpecs } from "@blocknote/core";
import AnalysisBlock from "./customBlocks/AnalysisBlock";
import TableChartBlock from "./customBlocks/TableChartBlock";

const customBlockSchema = BlockNoteSchema.create({
  blockSpecs: {
    ...defaultBlockSpecs,
    analysis: AnalysisBlock,
    "table-chart": TableChartBlock,
  },
});

export { customBlockSchema };
