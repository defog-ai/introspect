import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import DbCredentialsForm from "../components/extract-metadata/DBCredentialsForm";
import MetadataTable from "../components/extract-metadata/MetadataTable";
import SetupStatus from "../components/extract-metadata/SetupStatus"; // Adjust the import path as needed
import setupBaseUrl from "$utils/setupBaseUrl";
import { Select, Row, Col, Tabs, message } from "antd";
import Scaffolding from "$components/layout/Scaffolding";

const { TabPane } = Tabs;

const ExtractMetadata = () => {
  const router = useRouter();
  const apiKeyNames = (
    process.env.NEXT_PUBLIC_API_KEY_NAMES || "REPLACE_WITH_API_KEY_NAMES"
  ).split(",");
  const [apiKeyName, setApiKeyName] = useState(apiKeyNames[0]);
  const [token, setToken] = useState("");
  const [user, setUser] = useState("");
  const [userType, setUserType] = useState("");

  const [dbData, setDbData] = useState({}); // db_type and db_creds
  const [tablesData, setTablesData] = useState({}); // tables and indexed_tables
  const [metadata, setMetadata] = useState([]); // metadata of the tables

  const [dbConnectionstatus, setDbConnectionStatus] = useState(false);
  const [dbCredsUpdatedToggle, setDbCredsUpdatedToggle] = useState(false); // to trigger re render after db creds are updated

  const [loading, setLoading] = useState(false);

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

  return (
    <>
      <Meta />
      <Scaffolding id={"manage-database"} userType={"admin"}>
        <div className="w-full">
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
                  defaultValue={apiKeyName}
                />
              </Col>
            </Row>
          ) : null}
          <div className="mt-4">
            <SetupStatus
              loading={loading}
              isDatabaseSetupWell={dbConnectionstatus}
              isTablesIndexed={isTablesIndexed}
              hasNonEmptyDescription={hasNonEmptyDescription}
            />
          </div>

          <Tabs defaultActiveKey="1" className="w-full mt-4">
            <TabPane tab="Update Database Credentials" key="1">
              <DbCredentialsForm
                token={token}
                apiKeyName={apiKeyName}
                validateDatabaseConnection={validateDatabaseConnection}
                setDbConnectionStatus={setDbConnectionStatus}
                dbData={dbData}
                setDbData={setDbData}
                setDbCredsUpdatedToggle={setDbCredsUpdatedToggle}
              />
            </TabPane>
            <TabPane tab="Extract Metadata" key="2">
              <MetadataTable
                token={token}
                user={user}
                userType={userType}
                apiKeyName={apiKeyName}
                tablesData={tablesData}
                metadata={metadata} // Pass metadata as prop
              />
            </TabPane>
          </Tabs>
        </div>
      </Scaffolding>
    </>
  );
};

export default ExtractMetadata;
