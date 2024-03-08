// Creates a new editor instance.

import { getCursorColor } from "../../utils/utils";
import { customBlockSchema } from "./createCustomBlockSchema";
import { customSlashMenuItemList } from "./createCustomSlashMenuItems";

export const createEditorConfig = (
  initialBlocks = null,
  yjsDoc = null,
  yjsProvider = null,
  user = null
) => {
  return {
    blockSpecs: customBlockSchema,
    slashMenuItems: customSlashMenuItemList,
    defaultStyles: true,
    collaboration: {
      provider: yjsProvider,
      fragment: yjsDoc.getXmlFragment("document-store"),
      user: {
        name: user || "Anonymous-" + Math.floor(Math.random() * 100000),
        // random bright color using hsl
        color: getCursorColor(),
      },
    },
  };
};
