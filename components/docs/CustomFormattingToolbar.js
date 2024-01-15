import { useState } from "react";
import {
  BlockTypeDropdown,
  ColorStyleButton,
  CreateLinkButton,
  TextAlignButton,
  ToggledStyleButton,
  Toolbar,
  useEditorSelectionChange,
} from "@blocknote/react";
import "@blocknote/core/style.css";
import { aiBlocks } from "../../utils/utils";

export const CustomFormattingToolbar = ({ editor }) => {
  const [showToolBar, setShowToolBar] = useState(true);

  useEditorSelectionChange(editor, () => {
    setShowToolBar(
      aiBlocks.indexOf(editor.getTextCursorPosition()?.block?.type) === -1 &&
        editor.getSelection() !== undefined
    );
  });

  return showToolBar ? (
    <Toolbar>
      <BlockTypeDropdown editor={editor} />
      {/*Default button to toggle bold.*/}
      <ToggledStyleButton editor={editor} toggledStyle={"bold"} />
      {/*Default button to toggle italic.*/}
      <ToggledStyleButton editor={editor} toggledStyle={"italic"} />
      {/*Default button to toggle underline.*/}
      <ToggledStyleButton editor={editor} toggledStyle={"underline"} />
      <ToggledStyleButton editor={editor} toggledStyle={"strike"} />

      <TextAlignButton editor={editor} textAlignment={"left"} />
      <TextAlignButton editor={editor} textAlignment={"center"} />
      <TextAlignButton editor={editor} textAlignment={"right"} />

      <ColorStyleButton editor={editor} />
      {/* <NestBlockButton editor={editor} />
      <UnnestBlockButton editor={editor} /> */}

      <CreateLinkButton editor={editor} />
    </Toolbar>
  ) : null;
};
