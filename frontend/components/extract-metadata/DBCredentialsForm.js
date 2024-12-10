import { useState, useEffect } from "react";
import { Form, Select, Input, Button, message } from "antd";
import setupBaseUrl from "$utils/setupBaseUrl";
import { DatabaseOutlined } from "@ant-design/icons";

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
  const [form] = Form.useForm();
  const [dbType, setDbType] = useState(dbData.db_type || "postgres");
  const [loading, setLoading] = useState(false);

  const dbOptions = [
    { value: "postgres", label: "PostgreSQL" },
    { value: "redshift", label: "Amazon Redshift" },
    { value: "snowflake", label: "Snowflake" },
    { value: "databricks", label: "Databricks" },
    { value: "bigquery", label: "Google BigQuery" },
    { value: "sqlserver", label: "Microsoft SQL Server" },
  ];

  const handleDbTypeChange = (value) => {
    setDbType(value);
    form.resetFields(); // Reset form fields when dbType changes
  };

  useEffect(() => {
    console.log("CALLING");
    const fetchData = async () => {
      if (Object.keys(dbData).length > 0) {
        // console.log(dbData);
        setDbType(dbData.db_type);
        form.setFieldsValue({
          db_type: dbData.db_type,
          ...dbData.db_creds,
        });

        try {
          const res = await validateDatabaseConnection(
            dbData.db_type,
            dbData.db_creds
          );
          // console.log("res", res);
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
  }, [dbData, form]);

  const handleSubmit = async (values) => {
    console.log("Received values of form: ", values);
    const { ...db_creds } = values;
    const payload = {
      db_creds: db_creds,
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
      console.log("data", data);
      if (data?.success === true) {
        // setDbData({ db_type: payload.db_type, db_creds: payload.db_creds });
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

  return (
    <div className="space-y-4 dark:bg-dark-bg-primary">
      <div className="flex flex-col items-center text-2xl mb-10">
        <DatabaseOutlined className="text-4xl mb-2 dark:text-dark-text-primary" />
        <span className="dark:text-dark-text-primary">Update Database Credentials</span>
      </div>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          db_type: dbType,
          ...dbData.db_creds,
        }}
        className="dark:text-dark-text-primary"
      >
        <Form.Item
          label="Database Type"
          name="db_type"
          className="dark:text-dark-text-primary"
        >
          <Select
            options={dbOptions}
            onChange={handleDbTypeChange}
            className="dark:bg-dark-bg-secondary dark:border-dark-border"
          />
        </Form.Item>

        {dbCredOptions[dbType].map((field) => (
          <Form.Item
            key={field}
            label={field.charAt(0).toUpperCase() + field.slice(1)}
            name={field}
            className="dark:text-dark-text-primary"
          >
            <Input
              placeholder={placeholders[field] || `Enter ${field}`}
              type={field === "password" ? "password" : "text"}
              className="dark:bg-dark-bg-secondary dark:border-dark-border dark:text-dark-text-primary"
            />
          </Form.Item>
        ))}

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            className="w-full dark:border-dark-border"
          >
            Update
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default DbCredentialsForm;
