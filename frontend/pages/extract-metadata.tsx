import { useState, useEffect, useMemo, useContext, useRef, useId } from "react";
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
import { NewDbCreation } from "$components/extract-metadata/NewDbCreation";
import { Database, Plus, Trash } from "lucide-react";

const ExtractMetadata = () => {
  const [dbInfo, setDbInfo] = useState<{
    [dbName: string]: DbInfo;
  }>({});

  const [selectedDbName, setSelectedDbName] = useState(null);

  const token = useRef("");
  const [loading, setLoading] = useState(true);

  const message = useContext(MessageManagerContext);

  useEffect(() => {
    token.current = localStorage.getItem("defogToken");

    const setup = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_db_names",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token }),
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
      }
    };

    setup();
  }, []);

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
        label: "Add new database",
      },
      ...options,
    ];

    return (
      <div className="flex flex-row my-6 w-full gap-2 items-center">
        {Object.keys(dbInfo).length > 0 && (
          <>
            <SingleSelect
              label="Select database"
              labelClassNames="font-bold text-sm"
              allowClear={false}
              allowCreateNewOption={false}
              options={options}
              value={selectedDbName || undefined}
              onChange={(val) => setSelectedDbName(val)}
              placeholder="Select your DB name"
              optionRenderer={(option) => {
                if (option.value === newDbOption) {
                  return (
                    <div className="flex items-center gap-2">
                      <Plus className="w-4" />
                      Add new database
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
  }, [selectedDbName]);

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
    ];
  }, [loading, selectedDbName, dbInfo]);

  if (loading) {
    return (
      <>
        <Meta />
        <Scaffolding id="manage-database" userType="admin">
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
      <Scaffolding id="manage-database" userType="admin">
        <div className="w-full dark:bg-dark-bg-primary px-2 md:px-0">
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
              <NewDbCreation
                token={token.current}
                onCreated={(dbName, dbInfo) => {
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
