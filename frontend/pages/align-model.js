import { useState, useEffect } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import setupBaseUrl from "$utils/setupBaseUrl";
import IMGO from "$components/align-model/IMGO";
import Instructions from "../components/align-model/Instructions";
import GoldenQueries from "../components/align-model/GoldenQueries";
import { message } from "antd";
import { SettingOutlined } from "@ant-design/icons";
import { Row, Col, Select } from "antd";

const AlignModel = () => {
  const [devMode, setDevMode] = useState(false);
  const [compulsoryGlossary, setCompulsoryGlossary] = useState("");
  const [prunableGlossary, setPrunableGlossary] = useState("");
  const [goldenQueries, setGoldenQueries] = useState([]); // [ { question: "", sql: "" }, ... ]
  const [token, setToken] = useState("");

  // loading states
  const [isLoading, setIsLoading] = useState(false);
  const [isUpdatingInstructions, setIsUpdatingInstructions] = useState(false);
  const [isUpdatingGoldenQueries, setIsUpdatingGoldenQueries] = useState(false);

  // state that triggers an update in the golden queries
  const [updatedGoldenQueriesToggle, setUpdatedGoldenQueriesToggle] =
    useState(false);

  const [apiKeyNames, setApiKeyNames] = useState([]);

  const getApiKeyNames = async (token) => {
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_api_key_names",
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
    setApiKeyNames(data.api_key_names);
    setApiKeyName(data.api_key_names[0]);
  };
  const [apiKeyName, setApiKeyName] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    getApiKeyNames(token);
  }, []);

  useEffect(() => {
    // get token
    const token = localStorage.getItem("defogToken");
    setToken(token);

    // after 100ms, get the glossary and golden queries
    getGlossaryGoldenQueries(devMode);
  }, [devMode, apiKeyName]);

  // triggers golden queries when updatedGoldenQueriesToggle is toggled
  useEffect(() => {
    updateGoldenQueries();
  }, [updatedGoldenQueriesToggle]);

  const getGlossaryGoldenQueries = async (dev) => {
    setIsLoading(true);
    const token = localStorage.getItem("defogToken");
    console.log("Right now, devMode is", dev);
    try {
      const res = await fetch(
        setupBaseUrl("http", `integration/get_glossary_golden_queries`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token,
            dev: dev,
            key_name: apiKeyName,
          }),
        }
      );
      const data = await res.json();
      setCompulsoryGlossary(data.glossary_compulsory);
      setPrunableGlossary(data.glossary_prunable_units);
      setGoldenQueries(data.golden_queries);
      setIsLoading(false);
    } catch (e) {
      console.error(e);
      setIsLoading(false);
      message.error(
        "Failed to get instructions. Are you sure you have updated your database credentials?"
      );
    }
  };

  const updateGlossary = async (
    compulsoryGlossary,
    prunableGlossary,
    setLoading
  ) => {
    setLoading(true);
    const res = await fetch(
      setupBaseUrl("http", `integration/update_glossary`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          glossary_compulsory: compulsoryGlossary,
          glossary_prunable_units: prunableGlossary,
          token,
          dev: devMode,
          key_name: apiKeyName,
        }),
      }
    );
    const data = await res.json();
    setLoading(false);
    if (data.status === "success") {
      message.success("Instructions updated successfully!");
    }
  };

  const updateGoldenQueries = async () => {
    if (token) {
      setIsUpdatingGoldenQueries(true);
      const res = await fetch(
        setupBaseUrl("http", `integration/update_golden_queries`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token,
            golden_queries: goldenQueries,
            dev: devMode,
            key_name: apiKeyName,
          }),
        }
      );

      const data = await res.json();
      setIsUpdatingGoldenQueries(false);
      if (data.status === "success") {
        message.success("Golden queries updated successfully!");
      }
    }
  };

  const updateMetadata = async (metadata, setLoading) => {
    try {
      setLoading(true);
      console.log("metadata", metadata);
      console.log("token", token);
      console.log("apiKeyName", apiKeyName);

      const res = await fetch(
        setupBaseUrl("http", `integration/update_metadata`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token: token,
            key_name: apiKeyName,
            metadata: metadata,
          }),
        }
      );
      const data = await res.json();
      setLoading(false);
      if (data.error) {
        message.error(data.error || "Error updating metadata");
      } else {
        message.success("Metadata updated successfully!");
      }
    } catch (error) {
      console.error("Error saving data:", error);
      message.error("Error saving data");
      setLoading(false);
    }
  };

  return (
    <>
      <Meta />
      <Scaffolding id="align-model" userType="admin">
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
        <div className="flex justify-center items-center flex-col p-1 mt-1">
          <h1>
            <SettingOutlined style={{ fontSize: "3em", color: "#1890ff" }} />{" "}
          </h1>
          <h1 className="text-3xl mt-4">Align Model</h1>
          <p className="m-4">
            Here, you can see the instructions and golden queries that the model
            is currently using to create SQL queries. Feel free to change them
            to get the best results.
          </p>
        </div>
        <div className="flex flex-col p-1 border border-gray-3200 rounded-lg">
          {/* {!!compulsoryGlossary && goldenQueries.length > 0 ? (
            <IMGO
              token={token}
              apiKeyName={apiKeyName}
              updateGlossary={updateGlossary}
              updateMetadata={updateMetadata}
            />
          ) : null} */}
          <Instructions
            title="Glossary"
            description="This the information about your data that the model considers when generating your SQL queries. Feel free to edit these instructions to get the best results."
            compulsoryGlossary={compulsoryGlossary}
            setCompulsoryGlossary={setCompulsoryGlossary}
            prunableGlossary={prunableGlossary}
            setPrunableGlossary={setPrunableGlossary}
            updateGlossary={updateGlossary}
            updateGlossaryLoadingFunction={setIsUpdatingInstructions}
            isLoading={isLoading}
            isUpdatingInstructions={isUpdatingInstructions}
          />
          <GoldenQueries
            token={token}
            apiKeyName={apiKeyName}
            goldenQueries={goldenQueries}
            setGoldenQueries={setGoldenQueries}
            isLoading={isLoading}
            isUpdatingGoldenQueries={isUpdatingGoldenQueries}
            setUpdatedGoldenQueriesToggle={setUpdatedGoldenQueriesToggle}
          />
        </div>
      </Scaffolding>
    </>
  );
};

export default AlignModel;
