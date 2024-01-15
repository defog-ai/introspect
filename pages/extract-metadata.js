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
  const [dbType, setDbType] = useState("databricks");
  const [dbCreds, setDbCreds] = useState({});
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(false);
  const [metadata, setMetadata] = useState([]);
  const [context, setContext] = useContext(Context);
  const router = useRouter();
  const [userType, setUserType] = useState("admin");

  const getTables = async() => {
    const token = context.token;
    const res = await fetch(`http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/get_tables_db_creds`, {
      method: "POST",
      body: JSON.stringify({
        token
      }),
    });
    const data = await res.json();
    if (!data.error) {
      setDbType(data["db_type"]);
      setDbCreds(data["db_creds"]);
      setTables(data["tables"]);
    }
  }

  const getMetadata = async() => {
    const token = context.token;
    const res = await fetch(`http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/get_metadata`, {
      method: "POST",
      body: JSON.stringify({
        token
      }),
    });
    const data = await res.json();
    if (!data.error) {
      setMetadata(data.metadata);
    }
  }

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
      })
    });

    // get the current status
  }, [context]);


  const dbCredOptions = {
    "postgres": ["host", "port", "username", "password", "database"],
    "mysql": ["host", "port", "username", "password", "database"],
    "redshift": ["host", "port", "username", "password", "database"],
    "snowflake": ["account", "warehouse", "username", "password"],
    "databricks": ["server_hostname", "access_token", "http_path", "schema"]
  }

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
                disabled={loading}
                onFinish={async (values) => {
                  values = {
                    ...values,
                    db_type: values['db_type'] || dbType,
                    token: context.token
                  }
                  const res = await fetch(`http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/generate_tables`, {
                    method: "POST",
                    body: JSON.stringify(values)
                  });
                  const data = await res.json();
                  setTables(data["tables"]);
                }}
              >

                <Form.Item name="db_type" label="Database Type">
                  <Select
                    style={{ width: "100%"}}
                    defaultValue={{
                      value: dbType,
                      label: dbType.toLocaleUpperCase()
                    }}
                    onChange={(e) => {
                      setDbType(e);
                    }}
                  >
                    <Option value="databricks">DataBricks</Option>
                    <Option value="mysql">MySQL</Option>
                    <Option value="postgres">PostgreSQL</Option>
                    <Option value="redshift">Redshift</Option>
                    <Option value="snowflake">Snowflake</Option>
                  </Select>
                </Form.Item>
                {/* create form inputs based on the value selected above */}
                {dbCredOptions[dbType] !== undefined && dbCredOptions[dbType].map((item) => {
                  return <Form.Item label={item} name={item}>
                    <Input style={{width: "100%"}} />
                  </Form.Item>
                })}
                <Form.Item wrapperCol={{ span: 24 }}>
                  <Button
                    type={"primary"}
                    style={{ width: "100%" }}
                    htmlType="submit"
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
                      `http://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/get_metadata`,
                      {
                        method: "POST",
                        body: JSON.stringify({
                          ...dbCreds,
                          tables: values["tables"],
                          token: context.token,
                        }),
                      }
                    );
                    const data = await res.json();
                    setLoading(false);
                    setMetadata(data["schema"]);
                  }}
                >
                  <Form.Item name="tables" label="Tables to index">
                    <Select
                      mode="multiple"
                      style={{ width: "100%", maxWidth: 400 }}
                    >
                      {tables.map((table) => (
                        <Option value={table}>{table}</Option>
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
                        initialValue={item.column_description}
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
              })
            }
          </Col>
        </Row>
      </Scaffolding>
    </>
  )
}

export default ExtractMetadata