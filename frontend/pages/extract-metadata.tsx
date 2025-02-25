import { useState, useEffect, useMemo, useContext, useRef } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import MetadataTable from "../components/extract-metadata/MetadataTable";
import SetupStatus from "../components/extract-metadata/SetupStatus";
import setupBaseUrl from "$utils/setupBaseUrl";
import Scaffolding from "$components/layout/Scaffolding";
import {
  MessageManagerContext,
  Tabs,
  SingleSelect,
  DropFiles,
  SpinningLoader,
} from "@defogdotai/agents-ui-components/core-ui";
import { DbInfo, getDbInfo } from "$utils/utils";
import DbCredentialsForm from "$components/extract-metadata/DBCredentialsForm";

const ExtractMetadata = () => {
  const router = useRouter();
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

        const dbNames = data.db_names;

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
  const isTablesIndexed =
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

  const tabs = useMemo(() => {
    if (!selectedDbName) return [];
    if (loading) return [];

    return [
      {
        name: "Update Database Credentials",
        content: (
          <DbCredentialsForm
            token={token.current}
            existingDbInfo={dbInfo[selectedDbName]}
            onDbUpdatedOrCreated={(dbName, dbInfo) => {
              setSelectedDbName(dbName);
              setDbInfo((prev) => ({ ...prev, [dbName]: dbInfo }));
            }}
          />
        ),
      },
      {
        name: "Extract Metadata",
        content: (
          <MetadataTable
            token={token.current}
            dbName={selectedDbName}
            tablesData={dbInfo[selectedDbName]}
            initialMetadata={dbInfo[selectedDbName].metadata}
            // setColumnDescriptionCheck={setColumnDescriptionCheck}
          />
        ),
      },
    ];
  }, [loading, selectedDbName, dbInfo]);

  console.log(selectedDbName, dbInfo, isTablesIndexed, hasNonEmptyDescription);

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
        <div className="w-full dark:bg-dark-bg-primary">
          {Object.keys(dbInfo).length > 1 && (
            <div className="mb-4 w-full">
              <SingleSelect
                options={Object.keys(dbInfo).map((db) => ({
                  value: db,
                  label: db,
                }))}
                value={selectedDbName || undefined}
                onChange={(val) => setSelectedDbName(val)}
                placeholder="Select your DB name"
                rootClassNames="w-full"
              />
            </div>
          )}

          {Object.keys(dbInfo).length ? (
            <>
              <div className="mt-4 flex items-center flex-row">
                <div>Can connect:{dbInfo[selectedDbName]?.can_connect}</div>
                <div>Tables indexed: {isTablesIndexed ? "Yes" : "No"}</div>
                <div>
                  Has non-empty description:{" "}
                  {hasNonEmptyDescription ? "Yes" : "No"}
                </div>
              </div>

              <div className="dark:bg-dark-bg-primary mt-4">
                <Tabs
                  rootClassNames="w-full dark:bg-dark-bg-primary"
                  tabs={tabs.map((tab) => ({
                    ...tab,
                    className:
                      "dark:bg-dark-bg-primary dark:text-dark-text-primary dark:hover:bg-dark-hover dark:border-dark-border",
                    selectedClassName:
                      "dark:bg-dark-hover dark:text-dark-text-primary dark:border-b-2 dark:border-blue-500",
                  }))}
                  disableSingleSelect={true}
                />
              </div>
            </>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 md:min-w-full gap-4 my-2 prose dark:prose-invert">
              <div className="col-span-2">
                <p className="text-sm">
                  You have no databases yet. You can either upload a CSV/Excel
                  file or enter your database credentials.
                </p>
              </div>
              <div className="col-span-1">
                <DbCredentialsForm
                  token={token.current}
                  existingDbInfo={dbInfo[selectedDbName]}
                  onDbUpdatedOrCreated={() => setSelectedDbName("")}
                />
              </div>
              <div className="col-span-1 prose dark:prose-invert">
                <p>Or upload a CSV/Excel file</p>
                <p className="text-xs ">
                  Your file will be used to create a database which you can then
                  query/create reports for
                </p>
                <DropFiles
                  showIcon={true}
                  rootClassNames="w-full h-full border flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-600 text-gray-400 dark:text-gray-200"
                  labelClassNames="text-gray-400 dark:text-gray-200"
                  iconClassNames="m-auto text-gray-400"
                />
              </div>
            </div>
          )}
        </div>
      </Scaffolding>
    </>
  );
};

export default ExtractMetadata;
