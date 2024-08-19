import { useState, useEffect } from "react";
import { Form, Select, Input, Button, message } from "antd";
import setupBaseUrl from "$utils/setupBaseUrl";
import { DatabaseOutlined } from "@ant-design/icons";

const dbCredOptions = {
  postgres: ["host", "port", "user", "password", "database"],
  redshift: ["host", "port", "user", "password", "database", "schema"],
  snowflake: ["account", "warehouse", "user", "password"],
  databricks: ["server_hostname", "access_token", "http_path", "schema"],
  bigquery: [],
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
    const fetchData = async () => {
      if (Object.keys(dbData).length > 0) {
        console.log(dbData);
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
          console.log("res", res);
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
    <div className="mx-auto bg-white shadow-md rounded-md p-6 mt-8 w-2/3">
      <div className="text-2xl mb-4 text-center">
        <DatabaseOutlined className="text-2xl mr-2" />
        Database Credentials
      </div>
      <Form
        form={form}
        onFinish={handleSubmit}
        initialValues={{ db_type: dbData.db_type, ...dbData }}
        layout="vertical"
      >
        <Form.Item label="Database Type">
          <Select
            options={dbOptions}
            onChange={handleDbTypeChange}
            value={dbType}
            loading={loading}
            disabled={loading}
          />
        </Form.Item>
        {dbCredOptions[dbType]?.map((field) => (
          <Form.Item
            key={field}
            name={field}
            label={field.charAt(0).toUpperCase() + field.slice(1)}
            rules={
              dbType !== "sqlserver"
                ? [{ required: true, message: `Please input the ${field}!` }]
                : []
            }
          >
            <Input
              type={
                field === "password" || field === "access_token"
                  ? "password"
                  : "text"
              }
              placeholder={
                dbType === "sqlserver" && field === "database"
                  ? "Leave blank if you want to query multiple databases inside the same server"
                  : placeholders?.[field] || `Enter ${field}`
              }
              className="w-full p-2 border rounded bg-gray-50 text-gray-700 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            />
          </Form.Item>
        ))}
        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            className="w-full bg-blue-500 hover:bg-blue-600 text-white"
            loading={loading}
            disabled={loading}
          >
            Update
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default DbCredentialsForm;
