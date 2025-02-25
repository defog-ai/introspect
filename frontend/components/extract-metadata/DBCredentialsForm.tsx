import { useState, useEffect, useContext, useRef } from "react";
import setupBaseUrl from "$utils/setupBaseUrl";
import { Database } from "lucide-react";
import {
  Button,
  Input,
  MessageManagerContext,
  SingleSelect,
} from "@defogdotai/agents-ui-components/core-ui";

import { DbInfo, DbType, DbCreds } from "$utils/utils";

const dbCredOptions: { [dbType in DbType]: Array<keyof DbCreds[dbType]> } = {
  postgres: ["host", "port", "user", "password", "database"],
  redshift: ["host", "port", "user", "password", "database", "schema"],
  snowflake: ["account", "warehouse", "user", "password"],
  databricks: ["server_hostname", "access_token", "http_path", "schema"],
  bigquery: ["credentials_file_content"],
  sqlserver: ["server", "database", "user", "password"],
};

const placeholders = {
  host: "host.docker.internal",
  port: "5432",
  user: "Database User",
  database: "Database Name",
  server_hostname: "Server Hostname",
  access_token: "Access Token",
  http_path: "HTTP Path",
  schema: "Schema",
};

const emptyDbCredsType: DbInfo = {
  db_name: "",
  db_type: "postgres",
  db_creds: {
    host: "",
    port: "",
    user: "",
    password: "",
    database: "",
  },
};

const DbCredentialsForm = ({
  dbName = "",
  token = "",
  setDbConnectionStatus = () => {},
  existingDbInfo = {},
  onDbUpdatedOrCreated = () => {},
}: {
  dbName: string;
  token: string;
  setDbConnectionStatus: (status: boolean) => void;
  existingDbInfo?: DbInfo | {};
  onDbUpdatedOrCreated: (dbName: string, dbInfo: DbInfo) => void;
}) => {
  const [loading, setLoading] = useState(false);
  const message = useContext(MessageManagerContext);

  const dbOptions = [
    { value: "postgres", label: "PostgreSQL" },
    { value: "redshift", label: "Amazon Redshift" },
    { value: "snowflake", label: "Snowflake" },
    { value: "databricks", label: "Databricks" },
    { value: "bigquery", label: "Google BigQuery" },
    { value: "sqlserver", label: "Microsoft SQL Server" },
  ];

  const [dbCredsType, setDbCredsType] = useState<DbInfo | null>({
    ...emptyDbCredsType,
    ...existingDbInfo,
  });

  // useEffect(() => {
  //   const fetchData = async () => {
  //     if (!dbCredsType) return;
  //     if (Object.keys(dbCredsType).length > 0) {
  //       // setDbType(dbCredsType.db_type);
  //       // setFormData({
  //       //   db_type: dbCredsType.db_type,
  //       //   ...dbCredsType.db_creds,
  //       // });

  //       try {
  //         const res = await validateDatabaseConnection(
  //           dbCredsType.db_type,
  //           dbCredsType.db_creds
  //         );
  //         if (res.status === "success") {
  //           setDbConnectionStatus(true);
  //           message.success("Database connection validated!");
  //         } else {
  //           message.error("Database connection is not valid.");
  //           setDbConnectionStatus(false);
  //         }
  //       } catch (error) {
  //         console.error("Validation error:", error);
  //         message.error("Failed to validate database connection.");
  //         setDbConnectionStatus(false);
  //       }
  //     }
  //   };

  //   fetchData();
  // }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      db_name: dbCredsType.db_name,
      db_type: dbCredsType.db_type,
      db_creds: dbCredsType.db_creds,
    };

    console.log(payload);

    try {
      setLoading(true);
      // first, check if the database connection is valid
      let res = await fetch(
        setupBaseUrl("http", `integration/validate_db_connection`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            token: token,
            ...dbCredsType,
          }),
        }
      );

      if (!res.ok) {
        setDbConnectionStatus(false);
        message.error(
          "Could not connect to this database. Are you sure that database credentials are valid, and that your machine has DB access?"
        );
        return;
      } else {
        setDbConnectionStatus(true);
        message.success("Database connection validated!");
      }

      res = await fetch(setupBaseUrl("http", `integration/update_db_creds`), {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (data?.success === true) {
        message.success("Database Credentials updated successfully!");
        onDbUpdatedOrCreated(dbName, dbCredsType);
      } else {
        message.error("Failed to update Database Credentials.");
      }
    } catch (e) {
      console.log(e);
      message.error(
        "Error fetching tables. Please check your logs for more information."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="prose dark:bg-dark-bg-primary">
      {existingDbInfo ? (
        <p className="dark:text-dark-text-primary">Update your credentials</p>
      ) : null}
      <form onSubmit={handleSubmit} className="space-y-4">
        <SingleSelect
          allowClear={false}
          label={"Database Type"}
          value={dbCredsType?.db_type || "postgres"}
          options={dbOptions}
          onChange={(value) => {
            setDbCredsType({ ...dbCredsType, db_type: value });
          }}
        />

        {!dbName && (
          <>
            <Input
              label={
                "Database nickname (This is for your reference so make it memorable)"
              }
              type="text"
              name="db_name"
              onChange={(e) => {
                setDbCredsType({ ...dbCredsType, db_name: e.target.value });
              }}
            />
          </>
        )}

        {dbCredsType?.db_type &&
          dbCredOptions[dbCredsType.db_type].map((field) => (
            <div key={field} className="mb-4">
              <Input
                label={field.charAt(0).toUpperCase() + field.slice(1)}
                type={field === "password" ? "password" : "text"}
                name={field}
                defaultValue={dbCredsType.db_creds?.[field] || ""}
                onChange={(e) => {
                  setDbCredsType({
                    ...dbCredsType,
                    db_creds: {
                      ...dbCredsType.db_creds,
                      [field]: e.target.value,
                    },
                  });
                }}
                placeholder={placeholders[field] || `Enter ${field}`}
              />
            </div>
          ))}

        <Button
          className="w-full justify-center p-2"
          variant="normal"
          disabled={loading}
        >
          {loading ? "Updating..." : "Update"}
        </Button>
      </form>
    </div>
  );
};

export default DbCredentialsForm;
