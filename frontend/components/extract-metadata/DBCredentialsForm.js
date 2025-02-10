import { useState, useEffect, useContext } from "react";
import setupBaseUrl from "$utils/setupBaseUrl";
import { DatabaseOutlined } from "@ant-design/icons";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";

const dbCredOptions = {
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

const DbCredentialsForm = ({
  token,
  apiKeyName,
  validateDatabaseConnection,
  setDbConnectionStatus,
  dbData = {},
  setDbData,
  setDbCredsUpdatedToggle,
}) => {
  const [formData, setFormData] = useState({ db_type: dbData.db_type || "postgres", ...dbData.db_creds });
  const [dbType, setDbType] = useState(dbData.db_type || "postgres");
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

  const handleDbTypeChange = (e) => {
    const value = e.target.value;
    setDbType(value);
    setFormData({ db_type: value }); // Reset form fields when dbType changes
  };

  useEffect(() => {
    const fetchData = async () => {
      if (Object.keys(dbData).length > 0) {
        setDbType(dbData.db_type);
        setFormData({
          db_type: dbData.db_type,
          ...dbData.db_creds,
        });

        try {
          const res = await validateDatabaseConnection(
            dbData.db_type,
            dbData.db_creds
          );
          if (res.status === "success") {
            setDbConnectionStatus(true);
            message.success("Database connection validated!");
          } else {
            message.error("Database connection is not valid.");
            setDbConnectionStatus(false);
          }
        } catch (error) {
          console.error("Validation error:", error);
          message.error("Failed to validate database connection.");
          setDbConnectionStatus(false);
        }
      }
    };

    fetchData();
  }, [dbData]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const { db_type, ...db_creds } = formData;
    const payload = {
      db_creds,
      db_type: dbType,
      token: token,
      key_name: apiKeyName,
    };

    setLoading(true);
    // first, check if the database connection is valid
    const res = await validateDatabaseConnection(dbType, db_creds);
    if (res.status !== "success") {
      setDbConnectionStatus(false);
      message.error(
        "Could not connect to this database. Are you sure that database credentials are valid, and that your machine has DB access?"
      );
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(
        setupBaseUrl("http", `integration/update_db_creds`),
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      );
      const data = await res.json();
      if (data?.success === true) {
        message.success("Database Credentials updated successfully!");
        setDbCredsUpdatedToggle((prev) => !prev);
      } else {
        message.error("Failed to update Database Credentials.");
      }
    } catch (e) {
      console.log(e);
      message.error(
        "Error fetching tables. Please check your logs for more information."
      );
    }
    setLoading(false);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="space-y-4 dark:bg-dark-bg-primary">
      <div className="flex flex-col items-center text-2xl mb-10">
        <DatabaseOutlined className="text-4xl mb-2 dark:text-dark-text-primary" />
        <span className="dark:text-dark-text-primary">
          Update Database Credentials
        </span>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-primary mb-1">
            Database Type
          </label>
          <select
            name="db_type"
            value={dbType}
            onChange={handleDbTypeChange}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-dark-bg-secondary dark:border-dark-border dark:text-dark-text-primary"
          >
            {dbOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {dbType && dbCredOptions[dbType] && dbCredOptions[dbType].map((field) => (
          <div key={field} className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-primary mb-1">
              {field.charAt(0).toUpperCase() + field.slice(1)}
            </label>
            <input
              type={field === "password" ? "password" : "text"}
              name={field}
              value={formData[field] || ""}
              onChange={handleInputChange}
              placeholder={placeholders[field] || `Enter ${field}`}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-dark-bg-secondary dark:border-dark-border dark:text-dark-text-primary"
            />
          </div>
        ))}

        <button
          type="submit"
          disabled={loading}
          className="w-full px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 rounded-md shadow-sm disabled:opacity-50 disabled:cursor-not-allowed dark:border-dark-border"
        >
          {loading ? "Updating..." : "Update"}
        </button>
      </form>
    </div>
  );
};

export default DbCredentialsForm;
