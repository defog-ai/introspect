import { isValidFileType } from "$utils/utils";
import {
  DropFiles,
  MessageManagerContext,
  SpinningLoader,
} from "@defogdotai/agents-ui-components/core-ui";
import { useContext, useState } from "react";
import { twMerge } from "tailwind-merge";

export function DbUpload({
  token,
  uploadFile = () => {},
}: {
  token: string;
  uploadFile: ({
    fileName,
    fileBuffer,
  }: {
    fileName: string;
    fileBuffer: ArrayBuffer;
  }) => void;
}) {
  const [loading, setLoading] = useState(false);
  const message = useContext(MessageManagerContext);

  return (
    <div className="prose dark:prose-invert max-w-none">
      <h3>Upload data file</h3>
      <p>
        Don't have direct database access? Upload your CSV or Excel file to get
        started quickly.
      </p>
      <div className="h-96">
        <DropFiles
          showIcon={true}
          rootClassNames={twMerge("h-full", loading ? "hidden" : "")}
          label="Drag and drop your file here, or"
          onFileSelect={async (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            try {
              setLoading(true);

              let file = ev.target.files[0];
              if (!file) return;

              const fileType = isValidFileType(file?.type);

              if (!fileType) {
                throw new Error("Only CSV or Excel files are accepted");
              }

              const start = performance.now();

              const buf = await file.arrayBuffer();

              const end = performance.now();

              console.log(
                "Conversion to buffer took",
                end - start,
                "milliseconds"
              );

              try {
                message.info(`Uploading your file`);

                uploadFile({
                  fileName: file.name,
                  fileBuffer: buf,
                });
              } catch (e) {
                setLoading(false);
                message.error(e instanceof Error ? e.message : String(e));
              }
            } catch (e) {
              setLoading(false);
              message.error(e instanceof Error ? e.message : String(e));
            }
          }}
          onDrop={async (ev) => {
            ev.preventDefault();
            ev.stopPropagation();

            try {
              setLoading(true);

              let dataTransferObject: DataTransferItem =
                ev?.dataTransfer?.items?.[0];
              if (
                !dataTransferObject ||
                !dataTransferObject.kind ||
                dataTransferObject.kind !== "file"
              ) {
                throw new Error("Invalid file");
              }

              const fileType = isValidFileType(dataTransferObject.type);
              if (!fileType) {
                throw new Error("Only CSV or Excel files are accepted");
              }

              let file = dataTransferObject.getAsFile();

              const start = performance.now();

              const buf = await file.arrayBuffer();

              const end = performance.now();

              console.log(
                "Conversion to buffer took",
                end - start,
                "milliseconds"
              );

              try {
                message.info(
                  `Uploading your file. It might take upto 5 minutes to create a db if the file is large`
                );
                uploadFile({
                  fileName: file.name,
                  fileBuffer: buf,
                });
              } catch (e) {
                setLoading(false);
                message.error(e instanceof Error ? e.message : String(e));
              }
            } catch (e) {
              setLoading(false);
              message.error(e instanceof Error ? e.message : String(e));
            }
          }}
        />

        {loading && (
          <div className="border rounded-md dark:border-gray-700 text-xs min-h-96 flex w-full h-full items-center justify-center gap-1">
            <SpinningLoader /> Uploading your file
          </div>
        )}
      </div>
    </div>
  );
}
