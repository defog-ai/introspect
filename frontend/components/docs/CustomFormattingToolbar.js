import { useState, Fragment } from "react";
import {
  BasicTextStyleButton,
  BlockTypeDropdown,
  ColorStyleButton,
  CreateLinkButton,
  FormattingToolbar,
  TextAlignButton,
  ToggledStyleButton,
  Toolbar,
  useBlockNoteEditor,
  useEditorSelectionChange,
} from "@blocknote/react";
import "@blocknote/core/style.css";
import { aiBlocks } from "../../utils/utils";

export const CustomFormattingToolbar = () => {
  const [showToolBar, setShowToolBar] = useState(true);
  const editor = useBlockNoteEditor();

  useEditorSelectionChange(() => {
    setShowToolBar(
      aiBlocks.indexOf(editor.getTextCursorPosition()?.block?.type) === -1 &&
        editor.getSelection() !== undefined
    );
  }, editor);

  return showToolBar ? (
    <FormattingToolbar>
      <BlockTypeDropdown editor={editor} />
      {/*Default button to toggle bold.*/}
      <BasicTextStyleButton editor={editor} toggledStyle={"bold"} />
      {/*Default button to toggle italic.*/}
      <BasicTextStyleButton editor={editor} toggledStyle={"italic"} />
      {/*Default button to toggle underline.*/}
      <BasicTextStyleButton editor={editor} toggledStyle={"underline"} />
      <BasicTextStyleButton editor={editor} toggledStyle={"strike"} />

      <TextAlignButton editor={editor} textAlignment={"left"} />
      <TextAlignButton editor={editor} textAlignment={"center"} />
      <TextAlignButton editor={editor} textAlignment={"right"} />

      <ColorStyleButton editor={editor} />
      {/* <NestBlockButton editor={editor} />
      <UnnestBlockButton editor={editor} /> */}

      <CreateLinkButton editor={editor} />
    </FormattingToolbar>
  ) : null;
};
