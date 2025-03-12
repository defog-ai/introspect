import { isValidFileType } from "$utils/utils";
import {
  Button,
  DropFiles,
  MessageManagerContext,
  SpinningLoader,
} from "@defogdotai/agents-ui-components/core-ui";
import { useContext, useState } from "react";
import { twMerge } from "tailwind-merge";

export function ProjectCreationViaFiles({
  uploadFiles = () => {},
  fileUploading,
}: {
  uploadFiles: (files: File[]) => void;
  fileUploading: boolean;
}) {
  const message = useContext(MessageManagerContext);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  return (
    <div className="h-96 relative">
      <DropFiles
        disabled={fileUploading}
        acceptedFileTypes={[".csv", ".xls", ".xlsx", ".pdf"]}
        showIcon={true}
        allowMultiple={true}
        selectedFiles={selectedFiles}
        onRemoveFile={(index) => {
          if (fileUploading || !selectedFiles.length) return;
          console.time("OracleNewDb:onRemoveFile");
          setSelectedFiles(selectedFiles.filter((_, i) => i !== index));
          console.timeEnd("OracleNewDb:onRemoveFile");
        }}
        onFileSelect={async (ev) => {
          console.time("OracleNewDb:onFileSelect");
          ev.preventDefault();
          ev.stopPropagation();
          try {
            // this is when the user selects a file from the file dialog
            let files = ev.target.files;

            for (let file of files) {
              if (!file || !isValidFileType(file.type, true)) {
                throw new Error("Only CSV or Excel files are accepted");
              }
            }

            setSelectedFiles([...selectedFiles, ...files]);
          } catch (e) {
            console.error(e);
            message.error("Failed to parse the file");
          }
          console.timeEnd("OracleNewDb:onFileSelect");
        }}
        onDrop={async (ev) => {
          console.time("OracleNewDb:onDrop");
          ev.preventDefault();
          ev.stopPropagation();

          try {
            let dataTransferObjects: DataTransferItemList =
              ev?.dataTransfer?.items;

            let files: File[] = [];

            for (let dataTransferObject of dataTransferObjects) {
              if (
                !dataTransferObject ||
                !dataTransferObject.kind ||
                dataTransferObject.kind !== "file"
              ) {
                throw new Error("Invalid file");
              }

              if (!isValidFileType(dataTransferObject.type, true)) {
                throw new Error("Only CSV, Excel or PDF files are accepted");
              }

              let file = dataTransferObject.getAsFile();

              files.push(file);
            }
            setSelectedFiles([...selectedFiles, ...files]);
          } catch (e) {
            message.error(e.message || "Failed to parse the file");
            console.log(e.stack);
          }
          console.timeEnd("OracleNewDb:onDrop");
        }}
      />

      <Button
        className={twMerge(
          "absolute bottom-10 p-4 left-0 right-0 mx-auto w-fit rounded-full z-[10] shadow-md",
          fileUploading || !selectedFiles.length ? "pointer-events-none" : ""
        )}
        disabled={selectedFiles.length === 0 || fileUploading}
        variant="primary"
        onClick={async () => {
          try {
            uploadFiles(selectedFiles);
          } catch (e) {
            console.error(`Error during file upload:`, e);
            message.error(e.message || "Failed to upload files");
          } finally {
          }
        }}
      >
        {selectedFiles.length ? (
          fileUploading ? (
            <>
              <SpinningLoader />
              {"Uploading"}
            </>
          ) : (
            "Click to upload"
          )
        ) : (
          "Select some files"
        )}
      </Button>
    </div>
  );
}
