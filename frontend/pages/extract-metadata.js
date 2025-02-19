import { useState, useEffect, useMemo, useContext } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import DbCredentialsForm from "../components/extract-metadata/DBCredentialsForm";
import MetadataTable from "../components/extract-metadata/MetadataTable";
import SetupStatus from "../components/extract-metadata/SetupStatus";
import setupBaseUrl from "$utils/setupBaseUrl";
import Scaffolding from "$components/layout/Scaffolding";
import {
  MessageManagerContext,
  Tabs,
  SingleSelect,
} from "@defogdotai/agents-ui-components/core-ui";

const ExtractMetadata = () => {
  const router = useRouter();
  const [apiKeyNames, setApiKeyNames] = useState([]);
  const [apiKeyName, setApiKeyName] = useState(null);

  const getApiKeyNames = async (token) => {
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
    setApiKeyNames(data.db_names);
    setApiKeyName(data.db_names[0]);
  };

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    getApiKeyNames(token);
  }, []);

  const [token, setToken] = useState("");
  const [user, setUser] = useState("");
  const [userType, setUserType] = useState("");
  const [dbData, setDbData] = useState({});
  const [tablesData, setTablesData] = useState({});
  const [metadata, setMetadata] = useState([]);
  const [dbConnectionstatus, setDbConnectionStatus] = useState(false);
  const [dbCredsUpdatedToggle, setDbCredsUpdatedToggle] = useState(false);
  const [columnDescriptionCheck, setColumnDescriptionCheck] = useState(true);
  const [loading, setLoading] = useState(false);

  const message = useContext(MessageManagerContext);

  useEffect(() => {
    const fetchUserData = async () => {
      const user = localStorage.getItem("defogUser");
      const userType = localStorage.getItem("defogUserType");
      const token = localStorage.getItem("defogToken");

      setUser(user);
      setUserType(userType);
      setToken(token);

      if (user && token && userType) {
        if (!apiKeyName) return
          /**
           * This is because there are 2 triggers during page load
           * 1. The page loads and apiKeyName is null
           * 2. getApiKeyNames finishes and apiKeyName is set
           *
           * If we don't check for apiKeyName, we will make requests where
           * apiKeyName is null and the request will fail
           */
          await getTablesAndDbCreds(token, apiKeyName);
          await fetchMetadata(token, apiKeyName);
      } else {
        router.push("/log-in");
      }
    };

    fetchUserData();
  }, [apiKeyName, dbCredsUpdatedToggle]);
  
  const getTablesAndDbCreds = async (token, keyName) => {
    setLoading(true);
    const res = await fetch(
      setupBaseUrl("http", `integration/get_tables_db_creds`),
      {
        method: "POST",
        body: JSON.stringify({ token, db_name: keyName }),
        headers: { "Content-Type": "application/json" },
      }
    );
    if (res.status === 401) {
      message.error("Your credentials are incorrect. Please log in again.");
      setLoading(false);
      return;
    }
    const data = await res.json();
    if (!data.error) {
      setTablesData({
        tables: data["tables"],
        indexed_tables: data["selected_tables"],
      });
      setDbData({ db_type: data["db_type"], db_creds: data["db_creds"] });
    }
    setLoading(false);
  };

  const fetchMetadata = async (token, keyName) => {
    setLoading(true);
    const res = await fetch(setupBaseUrl("http", `integration/get_metadata`), {
      method: "POST",
      body: JSON.stringify({ token, db_name: keyName }),
      headers: { "Content-Type": "application/json" },
    });
    if (res.status === 401) {
      message.error("Your credentials are incorrect. Please log in again.");
      setLoading(false);
      return;
    }
    const data = await res.json();
    setLoading(false);
    if (!data.error) {
      setMetadata(data.metadata || []);
    } else {
      setMetadata([]);
    }
  };

  const validateDatabaseConnection = async (db_type, db_creds) => {
    const payload = {
      db_type,
      db_creds,
      token,
      key_name: apiKeyName,
    };
    try {
      const response = await fetch(
        setupBaseUrl("http", `integration/validate_db_connection`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      const data = await response.json();
      console.log("Validation response:", data);
      return data;
    } catch (error) {
      console.error("Error validating database connection:", error);
      throw new Error("Network error during database validation.");
    }
  };

  // Are any tables indexed?
  const isTablesIndexed =
    tablesData &&
    tablesData.indexed_tables &&
    tablesData.indexed_tables.length > 0;

  // If at least one column has a non-empty description
  const hasNonEmptyDescription = metadata.some(
    (item) => item.column_description && item.column_description.trim() !== ""
  );

  const tabs = useMemo(() => {
    return [
      {
        name: "Update Database Credentials",
        content: (
          <DbCredentialsForm
            token={token}
            apiKeyName={apiKeyName}
            validateDatabaseConnection={validateDatabaseConnection}
            setDbConnectionStatus={setDbConnectionStatus}
            dbData={dbData}
            setDbData={setDbData}
            setDbCredsUpdatedToggle={setDbCredsUpdatedToggle}
          />
        ),
      },
      {
        name: "Extract Metadata",
        content: (
          <MetadataTable
            token={token}
            apiKeyName={apiKeyName}
            tablesData={tablesData}
            initialMetadata={metadata}
            setColumnDescriptionCheck={setColumnDescriptionCheck}
          />
        ),
      },
    ];
  }, [
    token,
    apiKeyName,
    validateDatabaseConnection,
    setDbConnectionStatus,
    dbData,
    setDbData,
    setDbCredsUpdatedToggle,
    tablesData,
    metadata,
    setColumnDescriptionCheck,
  ]);

  return (
    <>
      <Meta />
      <Scaffolding id="manage-database" userType="admin">
        <div className="w-full dark:bg-dark-bg-primary">
          {apiKeyNames.length > 1 && (
            <div className="mb-4 w-full">
              <SingleSelect
                options={apiKeyNames.map((db) => ({
                  value: db,
                  label: db,
                }))}
                value={apiKeyName || undefined}
                onChange={(val) => setApiKeyName(val)}
                placeholder="Select your DB name"
                rootClassNames="w-full"
              />
            </div>
          )}

          <div className="mt-4">
            <SetupStatus
              loading={loading}
              isDatabaseSetupWell={dbConnectionstatus}
              isTablesIndexed={isTablesIndexed}
              hasNonEmptyDescription={
                hasNonEmptyDescription && columnDescriptionCheck
              }
            />
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
        </div>
      </Scaffolding>
    </>
  );
};

export default ExtractMetadata;
