import React, { useState, useContext, useEffect } from "react";
import { useRouter } from "next/router";
import { Context } from "../components/common/Context";
import Meta from "../components/common/Meta";
import Scaffolding from "../components/common/Scaffolding";
import {
  Input,
  Select,
  Form,
  Tooltip,
  Button,
  Row,
  Col,
  message,
} from "antd/lib";

const ExtractMetadata = () => {
  const { Option } = Select;
  const [dbType, setDbType] = useState(null);
  const [dbCreds, setDbCreds] = useState({});
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(false);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [metadata, setMetadata] = useState([]);
  const [context, setContext] = useContext(Context);
  const [selectedTables, setSelectedTables] = useState([]);
  const router = useRouter();
  const [userType, setUserType] = useState("admin");

  const getTables = async () => {
    const token = context.token;
    if (!token) {
      return;
    }
    const res = await fetch(
      `http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/get_tables_db_creds`,
      {
        method: "POST",
        body: JSON.stringify({
          token,
        }),
      }
    );
    const data = await res.json();
    if (!data.error) {
      // reset the current values in the db_creds form
      console.log(data);

      setDbType(data["db_type"]);
      setDbCreds(data["db_creds"]);
      setTables(data["tables"]);
      setSelectedTables(data["selected_tables"]);
    }
  };

  const getMetadata = async () => {
    const token = context.token;
    if (!token) {
      return;
    }
    const res = await fetch(
      `http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/get_metadata`,
      {
        method: "POST",
        body: JSON.stringify({
          token,
        }),
      }
    );
    const data = await res.json();
    if (!data.error) {
      setMetadata(data?.metadata || []);
    }
  };

  const generateMetadata = async () => {
    const token = context.token;
    if (!token) {
      return;
    }
    const res = await fetch(
      `http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/generate_metadata`,
      {
        method: "POST",
        body: JSON.stringify({
          token,
        }),
      }
    );
    const data = await res.json();
    if (!data.error) {
      setMetadata(data?.metadata || []);
    }
  };

  useEffect(() => {
    setLoading(true);
    let userType = context.userType;
    let token = context.token;
    if (!userType) {
      // load from local storage and set context
      const user = localStorage.getItem("defogUser");
      token = localStorage.getItem("defogToken");
      userType = localStorage.getItem("defogUserType");

      if (!user || !token || !userType) {
        // redirect to login page
        router.push("/login");
        return;
      }
      setContext({
        user: user,
        token: token,
        userType: userType,
      });
    }
    setUserType(userType);
    if (userType === undefined) {
      router.push("/login");
    } else if (userType !== "admin") {
      router.push("/");
    }

    // get the db creds and preloaded tables
    getTables().then(() => {
      getMetadata().then(() => {
        setLoading(false);
      });
    });

    // get the current status
  }, [context, context.token]);

  const dbCredOptions = {
    postgres: ["host", "port", "user", "password", "database"],
    mysql: ["host", "port", "user", "password", "database"],
    redshift: ["host", "port", "user", "password", "database"],
    snowflake: ["account", "warehouse", "user", "password"],
    databricks: ["server_hostname", "access_token", "http_path", "schema"],
  };

  return (
    <>
      <Meta />
      <Scaffolding id={"manage-database"} userType={"admin"}>
        <h1 style={{ paddingBottom: "1em" }}>Extract Metadata</h1>
        {/* select database type */}

        <Row type={"flex"} height={"100vh"}>
          <Col md={{ span: 8 }} xs={{ span: 24 }}>
            <div>
              <Form
                name="db_creds"
                labelCol={{ span: 8 }}
                wrapperCol={{ span: 16 }}
                style={{ maxWidth: 400 }}
                disabled={tablesLoading}
                onFinish={async (values) => {
                  values = {
                    db_creds: values,
                    db_type: values["db_type"] || dbType,
                    token: context.token,
                  };

                  setTablesLoading(true);
                  try {
                    const res = await fetch(
                      `http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/generate_tables`,
                      {
                        method: "POST",
                        body: JSON.stringify(values),
                      }
                    );
                    const data = await res.json();
                    setTables(data["tables"]);
                  } catch (e) {
                    console.log(e);
                  }
                  setTablesLoading(false);
                }}
              >
                <Form.Item name="db_type" label="Database Type">
                  <Select
                    style={{ width: "100%" }}
                    onChange={(e) => {
                      setDbType(e);
                    }}
                    // we need this key for default value to reflect when we update dbType from the useEffect
                    key={"db-type-" + dbType}
                    defaultValue={dbType}
                    options={[
                      "databricks",
                      "mysql",
                      "postgres",
                      "redshift",
                      "snowflake",
                    ].map((item) => {
                      return { value: item, key: item, label: item };
                    })}
                  />
                </Form.Item>
                {/* create form inputs based on the value selected above */}
                {dbCredOptions[dbType] !== undefined &&
                  dbCredOptions[dbType].map((item) => {
                    return (
                      <Form.Item
                        label={item}
                        name={item}
                        key={dbType + "_" + item + "_" + dbCreds[item]}
                        initialValue={dbCreds[item]}
                      >
                        <Input style={{ width: "100%" }} />
                      </Form.Item>
                    );
                  })}
                <Form.Item wrapperCol={{ span: 24 }}>
                  <Button
                    type={"primary"}
                    style={{ width: "100%" }}
                    htmlType="submit"
                    loading={loading}
                  >
                    Get Tables
                  </Button>
                </Form.Item>
              </Form>

              {tables.length > 0 && (
                <Form
                  name="db_tables"
                  labelCol={{ span: 8 }}
                  wrapperCol={{ span: 16 }}
                  style={{ maxWidth: 400 }}
                  disabled={loading}
                  onFinish={async (values) => {
                    setLoading(true);
                    const res = await fetch(
                      `http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/generate_metadata`,
                      {
                        method: "POST",
                        body: JSON.stringify({
                          tables: values["tables"],
                          token: context.token,
                        }),
                      }
                    );
                    const data = await res.json();
                    setLoading(false);
                    setMetadata(data?.metadata || []);
                  }}
                >
                  <Form.Item
                    name="tables"
                    label="Tables to index"
                    value={selectedTables}
                  >
                    <Select
                      mode="multiple"
                      style={{ width: "100%", maxWidth: 400 }}
                      placeholder="Select tables to index"
                      defaultValue={selectedTables}
                      onChange={(e) => {
                        console.log(e);
                        setSelectedTables(e);
                      }}
                    >
                      {tables.map((table) => (
                        <Option value={table} key={table}>
                          {table}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                  <Form.Item wrapperCol={{ span: 24 }}>
                    <Button
                      type="primary"
                      style={{ width: "100%", maxWidth: 535 }}
                      htmlType="submit"
                    >
                      Extract Metadata
                    </Button>
                  </Form.Item>
                </Form>
              )}
            </div>
          </Col>

          <Col
            md={{ span: 16 }}
            xs={{ span: 24 }}
            style={{ paddingRight: "2em", height: 600, overflowY: "scroll" }}
          >
            {metadata.length > 0 && (
              <Button
                type="primary"
                style={{ width: "100%", maxWidth: 535 }}
                disabled={loading}
                loading={loading}
                onClick={async () => {
                  setLoading(true);
                  const res = await fetch(
                    `http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/update_metadata`,
                    {
                      method: "POST",
                      body: JSON.stringify({
                        token: context.token,
                        metadata: metadata,
                      }),
                    }
                  );
                  const data = await res.json();
                  console.log(data);
                  setLoading(false);
                  if (
                    data["suggested_joins"] !== undefined &&
                    data["suggested_joins"] !== null &&
                    data["suggested_joins"] !== ""
                  ) {
                    // also update the value of the text area
                    document.getElementById("allowed-joins").value =
                      data["suggested_joins"];
                  }

                  message.success("Metadata updated successfully!");
                }}
              >
                Update metadata on server
              </Button>
            )}
            {metadata.length > 0 ? (
              <Row
                style={{
                  marginTop: "1em",
                  position: "sticky",
                  top: 0,
                  paddingBottom: "1em",
                  paddingTop: "1em",
                  backgroundColor: "white",
                  zIndex: 100,
                }}
              >
                <Col
                  xs={{ span: 24 }}
                  md={{ span: 4 }}
                  style={{ overflowWrap: "break-word" }}
                >
                  <b>Table Name</b>
                </Col>
                <Col
                  xs={{ span: 24 }}
                  md={{ span: 4 }}
                  style={{ overflowWrap: "break-word" }}
                >
                  <b>Column Name</b>
                </Col>
                <Col
                  xs={{ span: 24 }}
                  md={{ span: 4 }}
                  style={{ overflowWrap: "break-word" }}
                >
                  <b>Data Type</b>
                </Col>
                <Col xs={{ span: 24 }} md={{ span: 12 }}>
                  <b>Description (Optional)</b>
                </Col>
              </Row>
            ) : null}
            {metadata.length > 0 &&
              metadata.map((item, index) => {
                return (
                  <Row key={index} style={{ marginTop: "1em" }}>
                    <Col
                      xs={{ span: 24 }}
                      md={{ span: 4 }}
                      style={{ overflowWrap: "break-word" }}
                    >
                      {item.table_name}
                    </Col>
                    <Col
                      xs={{ span: 24 }}
                      md={{ span: 4 }}
                      style={{ overflowWrap: "break-word" }}
                    >
                      {item.column_name}
                    </Col>
                    <Col
                      xs={{ span: 24 }}
                      md={{ span: 4 }}
                      style={{ overflowWrap: "break-word" }}
                    >
                      {item.data_type}
                    </Col>
                    <Col xs={{ span: 24 }} md={{ span: 12 }}>
                      <Input.TextArea
                        key={index}
                        placeholder="Description of what this column does"
                        defaultValue={item.column_description}
                        autoSize={{ minRows: 2 }}
                        onChange={(e) => {
                          const newMetadata = [...metadata];
                          newMetadata[index]["column_description"] =
                            e.target.value;
                          setMetadata(newMetadata);
                        }}
                      />
                    </Col>
                  </Row>
                );
              })}
          </Col>
        </Row>
      </Scaffolding>
    </>
  );
};

export default ExtractMetadata;
