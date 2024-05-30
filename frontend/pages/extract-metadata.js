import React, { useState, useEffect } from "react";
import Meta from "$components/common/Meta";
import Scaffolding from "$components/common/Scaffolding";
import {
  Input,
  Select,
  Form,
  Button,
  Row,
  Col,
  Switch,
  message,
} from "antd/lib";
import setupBaseUrl from "$utils/setupBaseUrl";
import { FloatButton, Tabs } from "antd";

const ExtractMetadata = () => {
  const { Option } = Select;
  // const [apiKey, setApiKey] = useState("");
  // const [inference, setInference] = useState("api"); // either api or self-hosted
  const [dbType, setDbType] = useState("postgres");
  const [dbCreds, setDbCreds] = useState({});
  const [devMode, setDevMode] = useState(false);
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(false);
  const [metadata, setMetadata] = useState([]);
  const [selectedTablesForIndexing, setSelectedTablesForIndexing] = useState(
    []
  );
  const [filteredTables, setFilteredTables] = useState([]);
  const [token, setToken] = useState("");
  const [form] = Form.useForm();
  const [allowUpdates, setAllowUpdates] = useState("NO");

  const getTables = async () => {
    // load from local storage and
    const user = localStorage.getItem("defogUser");
    const token = localStorage.getItem("defogToken");
    setToken(token);
    const userType = localStorage.getItem("defogUserType");

    if (!user || !token || !userType) {
      // redirect to login page
      router.push("/log-in");
      return;
    }
    const res = await fetch(
      setupBaseUrl("http", `integration/get_tables_db_creds`),
      {
        method: "POST",
        body: JSON.stringify({ token }),
      }
    );
    const data = await res.json();
    if (!data.error) {
      // reset the current values in the db_creds form
      setDbType(data["db_type"]);
      setDbCreds(data["db_creds"]);
      setTables(data["tables"]);
      setSelectedTablesForIndexing(data["selected_tables"]);
      form.setFieldsValue({
        db_type: data["db_type"],
        ...data["db_creds"],
        db_tables: data["selected_tables"],
      });
    }
  };

  const getMetadata = async () => {
    const token = localStorage.getItem("defogToken");
    setToken(token);
    const res = await fetch(setupBaseUrl("http", `integration/get_metadata`), {
      method: "POST",
      body: JSON.stringify({ token }),
    });
    const data = await res.json();
    if (!data.error) {
      setMetadata(data?.metadata || []);
    }
  };

  useEffect(() => {
    setLoading(true);
    setAllowUpdates(
      process.env.NEXT_PUBLIC_ALLOW_UPDATES || "REPLACE_WITH_ALLOW_UPDATES"
    );
    // get the db creds and preloaded tables
    getTables().then(() => {
      getMetadata().then(() => {
        setLoading(false);
      });
    });

    // get the current status
  }, []);

  const dbCredOptions = {
    postgres: ["host", "port", "user", "password", "database"],
    redshift: ["host", "port", "user", "password", "database", "schema"],
    snowflake: ["account", "warehouse", "user", "password"],
    databricks: ["server_hostname", "access_token", "http_path", "schema"],
    bigquery: [],
  };

  return (
    <>
      <Meta />
      <Scaffolding id={"manage-database"} userType={"admin"}>
        <div className="w-10/12">
          <div className="pb-4 flex flex-row items-center mb-5">
            <h1 className="text-2xl font-bold">Extract Metadata</h1>
            <Switch
              className="ml-4"
              checkedChildren="Production"
              unCheckedChildren="Development"
              checked={!devMode}
              onChange={(e) => {
                console.log(e);
                setDevMode(!e);
                setMetadata([]);
              }}
            />
          </div>
          <Tabs
            rootClassName="manage-database-tabs"
            items={[
              {
                key: "db_creds",
                label: "Database Credentials",
                children: (
                  <div className="w-4/12 mb-10">
                    <Form
                      name="db_creds"
                      className=""
                      form={form}
                      disabled={loading}
                      onFinish={async (values) => {
                        setLoading(true);
                        values = {
                          db_creds: values,
                          db_type: values["db_type"] || dbType,
                          token: token,
                        };
                        try {
                          const res = await fetch(
                            setupBaseUrl("http", `integration/update_db_creds`),
                            {
                              method: "POST",
                              body: JSON.stringify(values),
                            }
                          );
                          const data = await res.json();
                          setLoading(false);
                          message.success(
                            "Database Credentials updated successfully!"
                          );

                          // also get the new list of tables
                          await getTables();
                        } catch (e) {
                          console.log(e);
                          setLoading(false);
                          message.error(
                            "Error fetching tables. Please check your docker logs for more informati)on."
                          );
                        }
                      }}
                    >
                      <Form.Item name="db_type" label="DB Type">
                        <Select
                          style={{ width: "100%" }}
                          onChange={(e) => {
                            setDbType(e);
                            if (e === "bigquery") {
                              // click the submit button
                              document
                                .getElementById("update-db-creds-btn")
                                .click();
                            }
                          }}
                          options={[
                            "databricks",
                            // "mysql",
                            "postgres",
                            "redshift",
                            "snowflake",
                            "bigquery",
                          ].map((item) => {
                            return { value: item, key: item, label: item };
                          })}
                        />
                      </Form.Item>
                      {/* create form inputs based on the value selected above */}
                      {dbCredOptions[dbType] !== undefined &&
                        dbCredOptions[dbType].map((item) => {
                          let toReturn;
                          if (item !== "password") {
                            toReturn = (
                              <Form.Item
                                label={item}
                                name={item}
                                key={dbType + "_" + item}
                              >
                                <Input style={{ width: "100%" }} />
                              </Form.Item>
                            );
                          } else {
                            toReturn = (
                              <Form.Item
                                label={item}
                                name={item}
                                key={dbType + "_" + item}
                              >
                                <Input.Password style={{ width: "100%" }} />
                              </Form.Item>
                            );
                          }
                          return toReturn;
                        })}
                      <Form.Item>
                        <Button
                          className="bg-white border border-gray-300 text-blue-500 hover:bg-blue-500 hover:text-white"
                          type={"primary"}
                          style={{ width: "100%" }}
                          htmlType="submit"
                          id="update-db-creds-btn"
                        >
                          Update DB Credentials
                        </Button>
                      </Form.Item>
                    </Form>
                  </div>
                ),
              },
              {
                key: "db_tables",
                label: "Extracted metadata",
                children: (
                  <div className="">
                    <Form
                      name="db_tables"
                      disabled={loading}
                      onFinish={async (values) => {
                        setLoading(true);
                        try {
                          message.info(
                            "Extracting metadata from selected tables. This can take up to 5 minutes. Please be patient."
                          );
                          const res = await fetch(
                            setupBaseUrl(
                              "http",
                              `integration/generate_metadata`
                            ),
                            {
                              method: "POST",
                              body: JSON.stringify({
                                tables: values["tables"],
                                token: token,
                                dev: devMode,
                              }),
                            }
                          );
                          const data = await res.json();
                          setLoading(false);
                          setMetadata(data?.metadata || []);
                        } catch (e) {
                          console.log(e);
                          setLoading(false);
                          message.error(
                            "Error fetching metadata - please look at your docker logs fo)r more information."
                          );
                        }
                      }}
                    >
                      <div className="flex flex-row">
                        <div className="w-4/12 mr-8">
                          <Form.Item
                            name="tables"
                            label="Select tables"
                            value={selectedTablesForIndexing}
                          >
                            <Select
                              mode="tags"
                              placeholder="Add tables to index"
                              onChange={(e) => {
                                console.log(e);
                                setSelectedTablesForIndexing(e);
                              }}
                            >
                              {tables.map((table) => (
                                <Option value={table} key={table}>
                                  {table}
                                </Option>
                              ))}
                            </Select>
                          </Form.Item>
                        </div>
                        <div className="w-2/12">
                          <Button
                            className="bg-white border border-gray-300 text-blue-500 hover:bg-blue-500 hover:text-white"
                            type="primary"
                            style={{ width: "100%", maxWidth: 535 }}
                            htmlType="submit"
                          >
                            Index tables
                          </Button>
                        </div>
                      </div>
                    </Form>
                    <div className="my-10">
                      {metadata.length > 0 ? (
                        <div className="mt-4 sticky top-0 py-4 z-50 shadow-md bg-white grid grid-cols-4 gap-4 font-bold">
                          <div className="border-r-2 p-2">
                            Table Name
                            <div className="table-filter">
                              <Select
                                mode="tags"
                                className="m-0 mt-4 w-full font-normal"
                                placeholder="Filter"
                                onChange={(e) => {
                                  setFilteredTables(e);
                                }}
                              >
                                {tables.map((table) => (
                                  <Option value={table} key={table}>
                                    {table}
                                  </Option>
                                ))}
                              </Select>
                            </div>
                          </div>
                          <div className="p-2 border-r-2">Column Name</div>
                          <div className="p-2 border-r-2">Data Type</div>
                          <div className="p-2">Description (Optional)</div>
                        </div>
                      ) : null}
                      {metadata.length > 0 &&
                        metadata.map((item, index) => {
                          if (
                            filteredTables.length > 0 &&
                            !filteredTables.includes(item.table_name)
                          ) {
                            return null;
                          }
                          return (
                            <div
                              className={
                                "py-4 grid grid-cols-4 gap-4 " +
                                (index % 2 === 1 ? "bg-gray-200" : "")
                              }
                              key={item.table_name + "_" + item.column_name}
                            >
                              <div className="p-2 border-r-2">
                                {item.table_name}
                              </div>
                              <div className="p-2 border-r-2">
                                {item.column_name}
                              </div>
                              <div className="p-2 border-r-2">
                                {item.data_type}
                              </div>
                              <div className="p-2">
                                <Input.TextArea
                                  key={index}
                                  placeholder="Description of what this column does"
                                  defaultValue={item.column_description || ""}
                                  autoSize={{ minRows: 2 }}
                                  onChange={(e) => {
                                    const newMetadata = [...metadata];
                                    newMetadata[index]["column_description"] =
                                      e.target.value;
                                    setMetadata(newMetadata);
                                  }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      {metadata.length > 0 && (
                        <FloatButton
                          rootClassName="w-96 *:rounded-md bg-orange-500 update-metadata-float"
                          type="primary"
                          description={"Update Metadata on servers"}
                          className="mt-5 "
                          disabled={loading}
                          loading={loading}
                          onClick={async () => {
                            setLoading(true);
                            const res = await fetch(
                              setupBaseUrl(
                                "http",
                                `integration/update_metadata`
                              ),
                              {
                                method: "POST",
                                body: JSON.stringify({
                                  metadata: metadata,
                                  token: token,
                                  dev: devMode,
                                }),
                              }
                            );
                            const data = await res.json();
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
                        ></FloatButton>
                      )}
                    </div>
                  </div>
                ),
              },
            ]}
          />
        </div>
      </Scaffolding>
    </>
  );
};

export default ExtractMetadata;
