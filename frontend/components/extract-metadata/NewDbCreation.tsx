import { FileSpreadsheet, Server } from "lucide-react";
import DbCredentialsForm from "./DBCredentialsForm";
import {
  DbInfo,
  isValidFileType,
  parseCsvFile,
  parseExcelFile,
  uploadFile,
} from "$utils/utils";
import {
  DropFiles,
  MessageManagerContext,
  Tabs,
} from "@defogdotai/agents-ui-components/core-ui";
import { useContext } from "react";

export function NewDbCreation({
  token,
  onCreated = () => {},
}: {
  token: string;
  onCreated: (dbName: string, dbInfo: DbInfo) => void;
}) {
  const message = useContext(MessageManagerContext);

  const tabs = [
    {
      name: (
        <div className="flex items-center gap-2">
          <Server className="w-4" />
          Connect Database
        </div>
      ),
      content: (
        <div className="prose dark:prose-invert max-w-none">
          <h3>Connect your database</h3>
          <p>
            Connect directly to your existing database to unlock AI-powered
            insights.
          </p>
          <DbCredentialsForm
            token={token}
            onDbUpdatedOrCreated={(dbName, dbInfo) => {
              onCreated(dbName, dbInfo);
            }}
          />
        </div>
      ),
    },
    {
      name: (
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="w-4" />
          Upload CSV/Excel
        </div>
      ),
      content: (
        <div className="prose dark:prose-invert max-w-none">
          <h3>Upload data file</h3>
          <p>
            Don't have direct database access? Upload your CSV or Excel file to
            get started quickly.
          </p>
          <DropFiles
            showIcon={true}
            rootClassNames="min-h-96 max-w-none border dark:border-gray-700  flex flex-col items-center justify-center bg-gray-50  dark:bg-gray-700 text-gray-400 dark:text-gray-200 p-4 w-full"
            labelClassNames="text-gray-400 dark:text-gray-200 text-sm"
            iconClassNames="m-auto text-gray-400 text-sm"
            label="Drag and drop your file here, or"
            onFileSelect={async (ev) => {
              ev.preventDefault();
              ev.stopPropagation();

              // this is when the user selects a file from the file dialog
              try {
                let file = ev.target.files[0];
                if (!file || !isValidFileType(file.type)) {
                  throw new Error("Only CSV or Excel files are accepted");
                }

                if (file.type === "text/csv") {
                  parseCsvFile(file, async ({ file, rows, columns }) => {
                    try {
                      const { dbName, dbInfo } = await uploadFile(
                        token,
                        file.name,
                        {
                          [file.name]: { rows, columns },
                        }
                      ).catch((e) => {
                        throw e;
                      });
                      onCreated(dbName, dbInfo);
                    } catch (e) {
                      throw e;
                    }
                  });
                } else {
                  parseExcelFile(file, async ({ file, sheets }) => {
                    try {
                      const { dbName, dbInfo } = await uploadFile(
                        token,
                        file.name,
                        sheets
                      ).catch((e) => {
                        throw e;
                      });

                      onCreated(dbName, dbInfo);
                    } catch (e) {
                      throw e;
                    }
                  });
                }
              } catch (e) {
                console.error(e);
                message.error("Failed to parse the file");
              }
            }}
            onDrop={async (ev) => {
              ev.preventDefault();
              ev.stopPropagation();
              try {
                let dataTransferObject: DataTransferItem =
                  ev?.dataTransfer?.items?.[0];
                if (
                  !dataTransferObject ||
                  !dataTransferObject.kind ||
                  dataTransferObject.kind !== "file"
                ) {
                  throw new Error("Invalid file");
                }

                let file = dataTransferObject.getAsFile();

                if (file.type === "text/csv") {
                  parseCsvFile(file, async ({ file, rows, columns }) => {
                    try {
                      const { dbName, dbInfo } = await uploadFile(
                        token,
                        file.name,
                        {
                          [file.name]: { rows, columns },
                        }
                      ).catch((e) => {
                        throw e;
                      });

                      onCreated(dbName, dbInfo);
                    } catch (e) {
                      throw e;
                    }
                  });
                } else {
                  parseExcelFile(file, async ({ file, sheets }) => {
                    try {
                      const { dbName, dbInfo } = await uploadFile(
                        token,
                        file.name,
                        sheets
                      ).catch((e) => {
                        throw e;
                      });

                      onCreated(dbName, dbInfo);
                    } catch (e) {
                      throw e;
                    }
                  });
                }
              } catch (e) {
                message.error(e.message || "Failed to parse the file");
                console.log(e.stack);
              } finally {
              }
            }}
          />
        </div>
      ),
    },
  ];

  return <Tabs tabs={tabs} />;
}
