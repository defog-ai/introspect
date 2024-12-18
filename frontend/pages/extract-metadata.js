import { useState, useEffect, useMemo, useContext } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import DbCredentialsForm from "../components/extract-metadata/DBCredentialsForm";
import MetadataTable from "../components/extract-metadata/MetadataTable";
import SetupStatus from "../components/extract-metadata/SetupStatus"; // Adjust the import path as needed
import setupBaseUrl from "$utils/setupBaseUrl";
import { Select, Row, Col } from "antd";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";
import Scaffolding from "$components/layout/Scaffolding";
import { Tabs } from "@defogdotai/agents-ui-components/core-ui";

const ExtractMetadata = () => {
  const router = useRouter();
  const [apiKeyNames, setApiKeyNames] = useState([]);

  const getApiKeyNames = async (token) => {
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_api_key_names",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
        }),
      }
    );
    if (!res.ok) {
      throw new Error(
        "Failed to get api key names - are you sure your network is working?"
      );
    }
    const data = await res.json();
    setApiKeyNames(data.api_key_names);
    setApiKeyName(data.api_key_names[0]);
  };
  const [apiKeyName, setApiKeyName] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    getApiKeyNames(token);
  }, []);
  const [token, setToken] = useState("");
  const [user, setUser] = useState("");
  const [userType, setUserType] = useState("");

  const [dbData, setDbData] = useState({}); // db_type and db_creds
  const [tablesData, setTablesData] = useState({}); // tables and indexed_tables
  const [metadata, setMetadata] = useState([]); // metadata of the tables

  const [dbConnectionstatus, setDbConnectionStatus] = useState(false);
  const [dbCredsUpdatedToggle, setDbCredsUpdatedToggle] = useState(false); // to trigger re render after db creds are updated

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
        await getTablesAndDbCreds(token, apiKeyName);
        await fetchMetadata(token, apiKeyName);
      } else {
        router.push("/log-in");
      }
    };

    fetchUserData();
  }, [apiKeyName, dbCredsUpdatedToggle]);

  const getTablesAndDbCreds = async (token, apiKeyName) => {
    setLoading(true);
    const res = await fetch(
      setupBaseUrl("http", `integration/get_tables_db_creds`),
      {
        method: "POST",
        body: JSON.stringify({
          token,
          key_name: apiKeyName,
        }),
      }
    );
    // check if the response has status 200
    if (res.status === 401) {
      message.error("Your credentials are incorrect. Please log in again.");
      return;
    }

    const data = await res.json();
    if (!data.error) {
      setTablesData({
        tables: data["tables"],
        indexed_tables: data["selected_tables"],
      });
      console.log("tablesData", data["tables"]);
      console.log("db_tables", data["selected_tables"]);
      setDbData({ db_type: data["db_type"], db_creds: data["db_creds"] });
    }
    setLoading(false);
  };

  const fetchMetadata = async (token, apiKeyName) => {
    setLoading(true);
    const res = await fetch(setupBaseUrl("http", `integration/get_metadata`), {
      method: "POST",
      body: JSON.stringify({
        token,
        key_name: apiKeyName,
      }),
    });
    // check if the response has status 200
    if (res.status === 401) {
      message.error("Your credentials are incorrect. Please log in again.");
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

  // Check if at least one table is indexed for defog
  const isTablesIndexed =
    tablesData &&
    tablesData.indexed_tables &&
    tablesData.indexed_tables.length > 0;

  // Check if at least one column has a non-empty description
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
            initialMetadata={metadata} // Pass metadata as
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
      <Scaffolding id={"manage-database"} userType={"admin"}>
        <div className="w-full dark:bg-dark-bg-primary">
          {apiKeyNames.length > 1 ? (
            <Row type={"flex"} height={"100vh"}>
              <Col span={24} style={{ paddingBottom: "1em" }}>
                <Select
                  style={{ width: "100%" }}
                  onChange={(e) => {
                    setApiKeyName(e);
                  }}
                  options={apiKeyNames.map((item) => {
                    return { value: item, key: item, label: item };
                  })}
                  value={apiKeyName}
                  className="dark:bg-dark-bg-secondary dark:border-dark-border"
                />
              </Col>
            </Row>
          ) : null}
          <div className="mt-4">
            <SetupStatus
              loading={loading}
              isDatabaseSetupWell={dbConnectionstatus}
              isTablesIndexed={isTablesIndexed}
              hasNonEmptyDescription={hasNonEmptyDescription && columnDescriptionCheck}
            />
          </div>

          <div className="dark:bg-dark-bg-primary">
            <Tabs
              rootClassNames="w-full mt-4 dark:bg-dark-bg-primary"
              tabs={tabs.map(tab => ({
                ...tab,
                className: 'dark:bg-dark-bg-primary dark:text-dark-text-primary dark:hover:bg-dark-hover dark:border-dark-border',
                selectedClassName: 'dark:bg-dark-hover dark:text-dark-text-primary dark:border-b-2 dark:border-blue-500'
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
