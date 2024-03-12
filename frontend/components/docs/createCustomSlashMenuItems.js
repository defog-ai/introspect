import { getDefaultReactSlashMenuItems } from "@blocknote/react";
import { v4 } from "uuid";

// Custom Slash Menu item which executes the above function.
const analysisSlashMenuItem = (editor) => ({
  title: "Analysis",
  onItemClick: () => {
    // Block that the text cursor is currently in.
    const currentBlock = editor.getTextCursorPosition().block;

    // New block we want to insert.
    const customBlock = {
      type: "analysis",
      props: {
        analysisId: "analysis-" + v4(),
      },
    };

    // Inserting the new block after the current one.
    editor.insertBlocks([customBlock], currentBlock);
  },
  aliases: ["analysis", "analyze"],
  group: "Data tools",
  icon: <p>x y</p>,
  subtext: "Run an analysis on your data.",
});

export const getCustomSlashMenuItems = (editor) => [
  analysisSlashMenuItem(editor),
  ...getDefaultReactSlashMenuItems(editor),
];
