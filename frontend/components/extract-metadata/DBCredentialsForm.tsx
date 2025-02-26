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

const emptyDbInfo: DbInfo = {
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
  existingDbInfo = null,
  onDbUpdatedOrCreated = () => {},
}: {
  dbName?: string;
  token: string;
  existingDbInfo?: DbInfo | null;
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

  const [dbInfo, setDbInfo] = useState<DbInfo | null>({
    ...emptyDbInfo,
    ...existingDbInfo,
  });

  useEffect(() => {
    if (!existingDbInfo) return;

    setDbInfo({
      ...emptyDbInfo,
      ...existingDbInfo,
    });
  }, [existingDbInfo]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      token: token,
      db_name: dbInfo.db_name,
      db_type: dbInfo.db_type,
      db_creds: dbInfo.db_creds,
    };

    console.log(payload);

    try {
      setLoading(true);
      const res = await fetch(
        setupBaseUrl("http", `integration/update_db_creds`),
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      );

      if (!res.ok) {
        throw Error("Could not update db creds");
      }

      const newDbInfo: DbInfo = await res.json();

      onDbUpdatedOrCreated(dbName, newDbInfo);
    } catch (e) {
      console.log(e);
      message.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="space-y-4 max-w-2xl not-prose">
        <SingleSelect
          allowClear={false}
          label={"Database Type"}
          value={dbInfo?.db_type || "postgres"}
          options={dbOptions}
          onChange={(value) => {
            setDbInfo({ ...dbInfo, db_type: value });
          }}
        />

        <Input
          label={
            "Database nickname (This is for your reference so make it memorable)"
          }
          status={
            !existingDbInfo || dbInfo?.db_name === existingDbInfo?.db_name
              ? null
              : "error"
          }
          type="text"
          name="db_name"
          value={dbInfo?.db_name || ""}
          onChange={(e) => {
            setDbInfo({ ...dbInfo, db_name: e.target.value });
          }}
        />
        {dbInfo?.db_type &&
          dbCredOptions[dbInfo.db_type].map((field) => (
            <div key={field}>
              <Input
                label={field.charAt(0).toUpperCase() + field.slice(1)}
                type={field === "password" ? "password" : "text"}
                name={field}
                value={dbInfo.db_creds?.[field] || ""}
                onChange={(e) => {
                  setDbInfo({
                    ...dbInfo,
                    db_creds: {
                      ...dbInfo.db_creds,
                      [field]: e.target.value,
                    },
                  });
                }}
                placeholder={placeholders[field] || `Enter ${field}`}
              />
            </div>
          ))}
        <Button
          onClick={handleSubmit}
          className="w-full justify-center p-2"
          variant="normal"
          disabled={loading}
        >
          {loading ? "Updating..." : !existingDbInfo ? "Create" : "Update"}
        </Button>
      </div>
    </>
  );
};

export default DbCredentialsForm;
