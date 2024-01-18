import React from "react";
import { AnalysisList } from "./AnalysisList";
import { DBCredsSidebar } from "./DBCredsSidebar";

export function DocSidebars() {
  return (
    <div id="doc-sidebars">
      {/* <DBCredsSidebar /> */}
      <AnalysisList />
    </div>
  );
}
