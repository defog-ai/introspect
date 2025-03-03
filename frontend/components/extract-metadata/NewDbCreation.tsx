import { FileSpreadsheet, Server } from "lucide-react";
import DbCredentialsForm from "./DBCredentialsForm";
import { DbInfo } from "$utils/utils";
import { Tabs } from "@defogdotai/agents-ui-components/core-ui";
import { useMemo } from "react";
import { DbUpload } from "./DbUpload";

export function NewDbCreation({
  token,
  uploadFile = () => {},
  onCredsSubmit = () => {},
}: {
  token: string;
  /**
   * If the user uploads a file, this web worker is used for processing.
   */
  uploadFile: ({
    fileName,
    fileBuffer,
  }: {
    fileName: string;
    fileBuffer: ArrayBuffer;
  }) => void;
  /**
   * When a user submits via the credentials tab.
   */
  onCredsSubmit: (dbName: string, dbInfo: DbInfo) => void;
}) {
  const tabs = useMemo(() => {
    return [
      {
        name: "connect-db",
        headerContent: (
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
                onCredsSubmit(dbName, dbInfo);
              }}
            />
          </div>
        ),
      },
      {
        name: "upload-file",
        headerContent: (
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-4" />
            Upload CSV/Excel
          </div>
        ),
        content: <DbUpload token={token} uploadFile={uploadFile} />,
      },
    ];
  }, []);

  return <Tabs tabs={tabs} />;
}
