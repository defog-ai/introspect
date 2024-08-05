import React, { useState, useEffect } from "react";
import Meta from "$components/layout/Meta";

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
import Scaffolding from "$components/layout/Scaffolding";
import { useRouter } from "next/router";

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
  const apiKeyNames = (
    process.env.NEXT_PUBLIC_API_KEY_NAMES || "REPLACE_WITH_API_KEY_NAMES"
  ).split(",");
  const [apiKeyName, setApiKeyName] = useState(apiKeyNames[0]);

  const router = useRouter();

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
    } else {
      setDbCreds({});
      setTables([]);
      setSelectedTablesForIndexing([]);
      form.setFieldsValue({
        db_type: "",
        db_tables: [],
        host: "",
        port: "",
        user: "",
        password: "",
        database: "",
        schema: "",
        account: "",
        warehouse: "",
        access_token: "",
        server_hostname: "",
        http_path: "",
      });
    }
  };

  const desc = {
    inning: "the inning number",
    batting_team: "name of the batting team",
    bowling_team: "name of the bowling team",
    batsman: "the player id of the batsman",
    bowler: "the player id of the bowler",
    batsman_name: "name of the batsman",
    non_striker: "name of the non-striker",
    bowler_name: "name of the bowler",
    bat_right_handed: "indicates whether the player is left or right handed",
    ovr: "the over number as a float. 2.4 would mean this was the 4th ball of the 3rd over. 0.1 would mean this was the first ball of the first",
    runs_batter: "the number of runs scored by the batsman on this ball",
    runs_w_extras: "the number of runs scored on this ball including extras",
    extras: "the number of extras scored on this ball",
    x: "x coordinate of where the ball ended up after it was hit. is 0 when it reaches the left-most region of the ground (the point boundary for a right hander) and is 360 when it reaches the right-most region of the ground (the point boundary for a right hander)",
    y: "y coordinate of where the ball ended up after it was hit. 'y' is 0 when the ball reaches the boundary straight down the ground (i.e., after a perfect straight drive), and is 360 when it reaches the boundary after going over the keeper's head",
    z: "the zone in which a ball was hit. z=1 is the fine-leg zone, z=2 is the zone behind square leg, z=3 is the zone in front of square leg etc. This progress all the way until z=8, which is the third-man area",
    landing_x:
      "the distance (in meters) away from the centre of the pitch that the ball lands. A negative value indicates the ball landed outside off-stump for a right-hander and outside leg-stump for a left-hander",
    landing_y:
      "the distance (in meters) away from the batsman stumps that a ball lands. A negative value indicates a full toss.",
    ended_x:
      "the distance (in meters) away from the centre of the pitch that the ball ends up when it reaches the batsman. A negative value indicates the ball landed outside off-stump for a right-hander and outside leg-stump for a left-hander.",
    ended_y:
      "the height (in meters) above the pitch by the time it reaches the batsman.",
    ball_speed: "the speed of the ball in miles per hour",
    cumul_runs:
      "the total number of runs scored by the batting team up to this point",
    wicket: "whether or not a wicket fell on this ball",
    wicket_method: "the method by which the wicket fell",
    who_out: "the name of the player who was out",
    control:
      "whether or not the batsman middled the ball (1=middled, 0=not middled)",
    extras_type: "the type of extras scored on this ball",
    match_id: "the id of the match",
    team1_name: "the name of the first team",
    team2_name: "the name of the second team",
    team1_id: "the id of the first team",
    team2_id: "the id of the second team",
    ground_name: "the name of the ground",
    ground_id: "the id of the ground",
    date: "the date of the match",
  };

  const getMetadata = async () => {
    const token = localStorage.getItem("defogToken");
    setToken(token);
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
  }, [apiKeyName]);

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
                          key_name: apiKeyName,
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
                                key_name: apiKeyName,
                              }),
                            }
                          );
                          const data = await res.json();
                          setLoading(false);
                          data.metadata.forEach((item) => {
                            if (desc[item.column_name]) {
                              item.column_description = desc[item.column_name];
                            }
                          });

                          setMetadata(data?.metadata || []);
                        } catch (e) {
                          console.log(e);
                          setLoading(false);
                          message.error(
                            "Error fetching metadata - please look at your docker logs for more information."
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
                        <div className="header mt-4 sticky top-0 py-4 z-50 shadow-md bg-white grid grid-cols-4 gap-4 font-bold">
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
                              <div className="table_name p-2 border-r-2">
                                {item.table_name}
                              </div>
                              <div className="column_name p-2 border-r-2">
                                {item.column_name}
                              </div>
                              <div className="data_type p-2 border-r-2">
                                {item.data_type}
                              </div>
                              <div className="column_description p-2">
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
                                  key_name: apiKeyName,
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
