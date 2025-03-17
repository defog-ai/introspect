import { useState, useEffect, useMemo, useContext, useRef, useId } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import MetadataTable from "../components/extract-metadata/MetadataTable";
import Scaffolding from "$components/layout/Scaffolding";
import {
  MessageManagerContext,
  Tabs,
  SingleSelect,
  SpinningLoader,
} from "@defogdotai/agents-ui-components/core-ui";
import { DbInfo, deleteDbInfo, getDbInfo } from "$utils/utils";
import DbCredentialsForm from "$components/extract-metadata/DBCredentialsForm";
import SetupStatus from "$components/extract-metadata/SetupStatus";
import { NewProjectCreation } from "$components/extract-metadata/NewProjectCreation";
import ProjectFiles from "$components/extract-metadata/ProjectFiles";
import { Database, Plus, Trash } from "lucide-react";

const ExtractMetadata = () => {
  const [dbInfo, setDbInfo] = useState<{
    [dbName: string]: DbInfo;
  }>({});

  const [selectedDbName, setSelectedDbName] = useState(null);

  const token = useRef("");
  const [loading, setLoading] = useState(true);
  const [fileUploading, setFileUploading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const message = useContext(MessageManagerContext);
  const router = useRouter();

  const uploadWorkerRef = useRef<Worker | null>(null);

  useEffect(() => {
    if (!uploadWorkerRef.current && typeof window !== "undefined") {
      uploadWorkerRef.current = new Worker(
        new URL(
          "../components/extract-metadata/db-upload-worker.ts",
          import.meta.url
        ),
        { type: "module" }
      );

      uploadWorkerRef.current.onmessage = (event) => {
        const { type, dbName, dbInfo, error } = event.data;

        if (type === "UPLOAD_SUCCESS") {
          message.success(`DB ${dbName} created successfully`);
          setDbInfo((prev) => ({ ...prev, [dbName]: dbInfo }));
          setSelectedDbName(dbName);
        } else if (type === "UPLOAD_ERROR") {
          message.error(error || "Failed to upload file");
        }
        setFileUploading(false);
      };
    }

    return () => {
      if (uploadWorkerRef.current) {
        uploadWorkerRef.current.terminate();
        uploadWorkerRef.current = null;
      }
    };
  }, [message]);

  useEffect(() => {
    const storedToken = localStorage.getItem("defogToken");
    token.current = storedToken;

    // Check if user is authenticated
    if (!storedToken) {
      setIsAuthenticated(false);
      setLoading(false);

      // Redirect to login page after a short delay
      setTimeout(() => {
        // Capture current URL with all query parameters
        const returnUrl = window.location.pathname + window.location.search;

        router.push({
          pathname: "/log-in",
          query: {
            message:
              "You are not logged in. Please log in to access database management.",
            returnUrl,
          },
        });
      }, 1500);
      return;
    }

    setIsAuthenticated(true);

    const setup = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_db_names",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: storedToken }),
          }
        );
        if (!res.ok) {
          throw new Error(
            "Failed to get api key names - are you sure your network is working?"
          );
        }

        const data = await res.json();

        const dbNames = data.db_names.filter((dbName) => dbName);

        const fetchedInfo = {};

        for (const dbName of dbNames) {
          const dbInfo = await getDbInfo(token.current, dbName);

          fetchedInfo[dbName] = dbInfo;
        }

        setSelectedDbName(data.db_names.length ? data.db_names[0] : null);
        setLoading(false);
        setDbInfo(fetchedInfo);
      } catch (e) {
        message.error(e.message);
        console.error(e);
        setLoading(false);
      }
    };

    setup();
  }, [router, message]);

  // Are any tables indexed?
  const areTablesIndexed =
    dbInfo[selectedDbName] &&
    dbInfo[selectedDbName].tables &&
    dbInfo[selectedDbName].tables.length > 0;

  // If at least one column has a non-empty description
  const hasNonEmptyDescription =
    dbInfo[selectedDbName] &&
    dbInfo[selectedDbName].metadata &&
    dbInfo[selectedDbName].metadata.some(
      (item) => item.column_description && item.column_description.trim() !== ""
    );

  const canConnect = dbInfo[selectedDbName]?.can_connect;

  const newDbOption = useId();

  const dbSelector = useMemo(() => {
    if (!Object.keys(dbInfo).length) return null;

    let options = Object.keys(dbInfo).map((db) => ({
      value: db,
      label: db,
    }));

    options = [
      {
        value: newDbOption,
        label: "Start a new project",
      },
      ...options,
    ];

    return (
      <div className="flex flex-row my-6 w-full gap-2 items-center">
        {Object.keys(dbInfo).length > 0 && (
          <>
            <SingleSelect
              disabled={fileUploading}
              label="Select a project"
              labelClassNames="font-bold text-sm"
              allowClear={false}
              allowCreateNewOption={false}
              options={options}
              value={selectedDbName || undefined}
              onChange={(val) => setSelectedDbName(val)}
              placeholder="Select your DB name"
              rootClassNames="flex-grow min-w-[250px] w-full"
              optionRenderer={(option) => {
                if (option.value === newDbOption) {
                  return (
                    <div className="flex items-center gap-2">
                      <Plus className="w-4" />
                      Start a new project
                    </div>
                  );
                }
                return (
                  <div className="whitespace-pre flex items-center gap-2">
                    <Database className="w-4" />
                    {option.label}
                  </div>
                );
              }}
            />
            {selectedDbName !== newDbOption && (
              <Trash
                className="w-5 h-5 relative top-3 cursor-pointer hover:text-rose-500"
                onClick={() => {
                  try {
                    deleteDbInfo(token.current, selectedDbName);
                    message.success("Database deleted");

                    setDbInfo((prev) => {
                      const newDbInfo = { ...prev };
                      delete newDbInfo[selectedDbName];

                      return newDbInfo;
                    });

                    setSelectedDbName(newDbOption);
                  } catch (e) {
                    console.error(e);
                    message.error("Failed to delete database");
                  }
                }}
              />
            )}
          </>
        )}
      </div>
    );
  }, [message, selectedDbName, fileUploading]);

  const tabs = useMemo(() => {
    if (!selectedDbName || selectedDbName === newDbOption) return null;
    if (loading) return null;

    return [
      {
        name: "Database Connection",
        content: (
          <>
            <DbCredentialsForm
              token={token.current}
              existingDbInfo={dbInfo[selectedDbName]}
              onDbUpdatedOrCreated={(dbName, dbInfo) => {
                setSelectedDbName(dbName);
                setDbInfo((prev) => ({ ...prev, [dbName]: dbInfo }));
              }}
            />
          </>
        ),
      },
      {
        name: "AI Metadata Management",
        content: (
          <>
            <MetadataTable
              token={token.current}
              dbInfo={dbInfo[selectedDbName]}
              onUpdate={(dbName, newDbInfo) => {
                setDbInfo((prev) => ({ ...prev, [dbName]: newDbInfo }));
              }}
            />
          </>
        ),
      },
      {
        name: "project-files",
        headerContent: (
          <div className="flex items-center">
            Project Files
            {dbInfo[selectedDbName]?.associated_files?.length > 0 && (
              <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full">
                {dbInfo[selectedDbName]?.associated_files?.length}
              </span>
            )}
          </div>
        ),
        content: (
          <>
            <ProjectFiles
              files={dbInfo[selectedDbName]?.associated_files || []}
              token={token.current}
              dbName={selectedDbName}
              onFilesUploaded={(dbName, newDbInfo) => {
                setDbInfo((prev) => ({ ...prev, [dbName]: newDbInfo }));
              }}
            />
          </>
        ),
      },
    ];
  }, [loading, selectedDbName, dbInfo]);

  if (!isAuthenticated && !loading) {
    return (
      <>
        <Meta />
        <div className="h-screen flex flex-col items-center justify-center">
          <div className="text-center p-6">
            <h2 className="text-xl font-semibold mb-2">Not Logged In</h2>
            <p className="mb-4">
              You are not logged in. Redirecting to login page...
            </p>
            <SpinningLoader />
          </div>
        </div>
      </>
    );
  }

  if (loading) {
    return (
      <>
        <Meta />
        <Scaffolding id="manage-database" userType="ADMIN">
          <div className="w-full h-96 text-gray-500 dark:bg-dark-bg-primary flex items-center justify-center">
            <SpinningLoader />
            Loading
          </div>
        </Scaffolding>
      </>
    );
  }

  return (
    <>
      <Meta />
      <Scaffolding id="manage-database" userType="ADMIN">
        <div className="w-full dark:bg-dark-bg-primary px-2 md:px-0 mb-4">
          {dbSelector}
          {Object.keys(dbInfo).length && tabs ? (
            <>
              <SetupStatus
                loading={loading}
                canConnect={canConnect}
                areTablesIndexed={areTablesIndexed}
                hasNonEmptyDescription={hasNonEmptyDescription}
              />
              <div className="dark:bg-dark-bg-primary mt-4">
                <Tabs
                  rootClassNames="w-full dark:bg-dark-bg-primary min-h-[500px]"
                  tabs={tabs.map((tab) => ({
                    ...tab,
                    className:
                      "!overflow-y-visible dark:bg-dark-bg-primary dark:text-dark-text-primary dark:hover:bg-dark-hover dark:border-dark-border",
                    selectedClassName:
                      "dark:bg-dark-hover dark:text-dark-text-primary dark:border-b-2 dark:border-blue-500",
                  }))}
                  disableSingleSelect={true}
                  contentClassNames="border dark:border-gray-700 border-t-none"
                />
              </div>
            </>
          ) : (
            <div className="prose dark:prose-invert max-w-none">
              {Object.keys(dbInfo).length === 0 && (
                <div className="max-w-lg mx-auto text-center my-10">
                  <h3>Welcome to Defog!</h3>
                  <p>
                    Let's get you set up with your first database connection.
                    Connect your data source to start generating AI-powered SQL
                    queries and reports.
                  </p>
                </div>
              )}
              <NewProjectCreation
                fileUploading={fileUploading}
                token={token.current}
                uploadFiles={(files) => {
                  setFileUploading(true);

                  uploadWorkerRef.current.postMessage({
                    type: "UPLOAD_FILE",
                    token: token.current,
                    files,
                  });
                }}
                onCredsSubmit={(dbName, dbInfo) => {
                  setDbInfo((prev) => ({ ...prev, [dbName]: dbInfo }));
                  setSelectedDbName(dbName);
                  message.success(`Database ${dbName} created successfully`);
                }}
              />
            </div>
          )}
        </div>
      </Scaffolding>
    </>
  );
};

export default ExtractMetadata;
