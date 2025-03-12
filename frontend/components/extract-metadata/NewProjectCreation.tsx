import { FileSpreadsheet, Server } from "lucide-react";
import DbCredentialsForm from "./DBCredentialsForm";
import { DbInfo } from "$utils/utils";
import { Tabs } from "@defogdotai/agents-ui-components/core-ui";
import { useMemo } from "react";
import { ProjectCreationViaFiles } from "./ProjectCreationViaFiles";

/**
 * Allows for project creation via both db creds and file uploads.
 */
export function NewProjectCreation({
  token,
  fileUploading,
  uploadFiles = () => {},
  onCredsSubmit = () => {},
}: {
  token: string;
  /**
   * If a file is being uploaded currently.
   */
  fileUploading: boolean;
  /**
   * If the user uploads a file, this web worker is used for processing.
   */
  uploadFiles: (files: File[]) => void;
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
            Upload CSV/Excel/PDFs
          </div>
        ),
        content: (
          <div className="prose dark:prose-invert max-w-none">
            <h3>Upload your files here</h3>
            <p>
              You can upload CSV/Excel for analysing them. You can upload PDFs
              to provide more context to the model when generating insights.
            </p>
            <ProjectCreationViaFiles
              fileUploading={fileUploading}
              uploadFiles={uploadFiles}
            />
          </div>
        ),
      },
    ];
  }, [fileUploading]);

  return <Tabs tabs={tabs} />;
}
