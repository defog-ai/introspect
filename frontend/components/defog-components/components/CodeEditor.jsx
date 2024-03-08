import React, { useState } from "react";
import ErrorBoundary from "./common/ErrorBoundary";

import dynamic from "next/dynamic";
import "@uiw/react-textarea-code-editor/dist.css";

const Editor = dynamic(
  () => import("@uiw/react-textarea-code-editor").then((mod) => mod.default),
  { ssr: false }
);

export function CodeEditor({
  analysisId = null,
  toolRunId = null,
  code = null,
  language = "sql",
  updateProp = null,
  className = "",
  handleEdit = () => {},
}) {
  const [toolCode, setToolCode] = useState(code);

  const updateCodeAndSql = (newVal) => {
    // update values of the code and the SQL
    if (updateProp !== "sql" && updateProp !== "code_str") return;
    if (!toolRunId) return;
    if (!analysisId) return;
    if (!newVal) return;

    handleEdit({
      tool_run_id: toolRunId,
      update_prop: updateProp,
      new_val: newVal,
      analysis_id: analysisId,
    });
    setToolCode(newVal);
  };

  return (
    <ErrorBoundary>
      <>
        <Editor
          language={language}
          className={`language-${language} ` + className}
          padding={15}
          value={toolCode}
          onChange={(evn) => {
            updateCodeAndSql(evn.target.value);
          }}
        />
      </>
    </ErrorBoundary>
  );
}
