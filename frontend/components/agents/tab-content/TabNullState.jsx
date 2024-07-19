import { useContext, useState } from "react";
import { parseCsvFile } from "../../agents-ui-components/lib/components/utils/utils";
import {
  DropFiles,
  MessageManagerContext,
  SingleSelect,
  SpinningLoader,
} from "../../agents-ui-components/lib/ui-components/lib/main";
import { ArrowDownTrayIcon } from "@heroicons/react/20/solid";

export function TabNullState({
  availableDbs = [],
  onSelectDb = (...args) => {},
  onParseCsv = (...args) => {},
  fileUploading = false,
}) {
  const messageManager = useContext(MessageManagerContext);

  return (
    <div className="w-full h-full flex flex-col gap-4 items-center justify-center">
      <SingleSelect
        rootClassNames="w-96 max-w-[90%] border p-4 rounded-md"
        label={"Please select a database"}
        options={availableDbs.map((d) => {
          d.value = d.name;
          d.label = d.name;
          return d;
        })}
        disabled={fileUploading}
        onChange={(nm) => {
          onSelectDb(nm);
        }}
      />
      <DropFiles
        label="Or drop a CSV"
        rootClassNames="w-96 max-w-[90%] border p-4 rounded-md text-gray-400"
        disabled={fileUploading}
        onFileSelect={(ev) => {
          ev.preventDefault();
          ev.stopPropagation();

          // this is when the user selects a file from the file dialog
          try {
            let file = ev.target.files[0];
            if (!file || file.type !== "text/csv") {
              throw new Error("Only CSV files are accepted");
            }

            parseCsvFile(file, onParseCsv);
          } catch (e) {
            messageManager.error("Failed to parse the file");
          }
        }}
        onDrop={(ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          try {
            let file = ev?.dataTransfer?.items?.[0];
            if (
              !file ||
              !file.kind ||
              file.kind !== "file" ||
              file.type !== "text/csv"
            ) {
              throw new Error("Only CSV files are accepted");
            }

            file = file.getAsFile();

            parseCsvFile(file, onParseCsv);
          } catch (e) {
            messageManager.error("Failed to parse the file");
            console.log(e.stack);
          }
        }}
        showIcon={false}
      >
        {fileUploading ? (
          <div className="text-sm">
            Uploading
            <SpinningLoader classNames="h-4 w-4 inline m-0 ml-2 text-gray-400" />
          </div>
        ) : (
          <>
            <span className="inline sm:hidden">Upload a CSV</span>
            <ArrowDownTrayIcon className="h-6 w-6 inline text-gray-400" />
          </>
        )}
      </DropFiles>
    </div>
  );
}
