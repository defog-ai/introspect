import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import Source from "$components/manage-sources/Source";
import setupBaseUrl from "$utils/setupBaseUrl";
import { useCallback, useContext, useEffect, useState } from "react";
import { Col, Input, Row, Select, Spin } from "antd";
import { BookOutlined } from "@ant-design/icons";
import {
  Button,
  MessageManagerContext,
} from "@defogdotai/agents-ui-components/core-ui";

const ManageSources = () => {
  const [apiKeyName, setApiKeyName] = useState(null);
  const [apiKeyNames, setApiKeyNames] = useState([]);
  const [inputLink, setInputLink] = useState("");
  const [importedSources, setImportedSources] = useState([]);
  const [waitImport, setWaitImport] = useState(false);
  const message = useContext(MessageManagerContext);

  const getApiKeyNames = async (token) => {
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_db_names",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
        }),
      }
    );
    if (!res.ok) {
      throw new Error(
        "Failed to get api key names - are you sure your network is working?"
      );
    }
    const data = await res.json();
    setApiKeyNames(data.db_names);
    setApiKeyName(data.db_names[0]);
  };

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    getApiKeyNames(token);
  }, []);

  const getSources = useCallback(async () => {
    try {
      const token = localStorage.getItem("defogToken");
      const response = await fetch(setupBaseUrl("http", `sources/list`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setImportedSources(data);
      } else {
        message.error("Failed to get sources");
      }
    } catch (e) {
      message.error(e.message);
      console.error(e);
    }
  }, [apiKeyName, setImportedSources]);

  const addSource = useCallback(async () => {
    try {
      const token = localStorage.getItem("defogToken");
      // make a request to /sources/import with token, key_name, and source
      setWaitImport(true);
      const response = await fetch(setupBaseUrl("http", `sources/import`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
          links: [inputLink],
        }),
      });

      if (response.ok) {
        message.info("Source added successfully");
        setInputLink("");
        getSources();
      } else {
        message.error("Failed to add source");
      }
    } catch (e) {
      message.error("Failed to add source");
      console.error(e);
    } finally {
      setWaitImport(false);
    }
  }, [apiKeyName, inputLink, setInputLink, getSources]);

  const deleteSource = useCallback(
    async (link) => {
      const token = localStorage.getItem("defogToken");
      const response = await fetch(setupBaseUrl("http", `sources/delete`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
          link: link,
        }),
      });
      if (response.ok) {
        message.info("Source deleted successfully");
        getSources();
      }
    },
    [apiKeyName, getSources]
  );

  useEffect(() => {
    if (apiKeyName) {
      getSources();
    }
  }, [apiKeyName]);

  return (
    <>
      <Meta />
      <Scaffolding id={"manage-users"} userType={"admin"}>
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
                value={apiKeyName}
              />
            </Col>
          </Row>
        ) : null}
        <div className="flex justify-center items-center flex-col p-1 mt-5">
          <h1>
            <BookOutlined style={{ fontSize: "3.5em", color: "#1890ff" }} />{" "}
          </h1>
          <h1 className="text-3xl mt-4">Manage Sources</h1>
        </div>
        <div className="flex justify-center items-center flex-col p-1">
          <div className="flex items-center w-full px-4 my-2">
            <Input
              value={inputLink}
              className="flex-grow p-3 border rounded-lg text-gray-700 focus:outline-none"
              onChange={(e) => setInputLink(e.target.value)}
              placeholder="Enter source link here"
            />
            <div className="ml-4">
              {waitImport ? (
                <Spin />
              ) : (
                <Button type="primary" className="" onClick={addSource}>
                  Add Source
                </Button>
              )}
            </div>
          </div>
        </div>
        <div className="flex flex-col p-1 mt-2">
          {Object.entries(importedSources).map(([link, source], i) => (
            <Source
              key={link}
              link={link}
              source={source}
              deleteSource={deleteSource}
            />
          ))}
        </div>
      </Scaffolding>
    </>
  );
};

export default ManageSources;
