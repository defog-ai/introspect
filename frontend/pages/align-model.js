import { useState, useEffect, useContext } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import setupBaseUrl from "$utils/setupBaseUrl";
import Instructions from "../components/align-model/Instructions";
import GoldenQueries from "../components/align-model/GoldenQueries";
import Guidelines from "../components/align-model/Guidelines";
import { SettingOutlined } from "@ant-design/icons";
import { MessageManagerContext, SingleSelect as Select, Tabs } from "@defogdotai/agents-ui-components/core-ui";

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
  const message = useContext(MessageManagerContext);

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
    if (!apiKeyName) return;
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
      // get instructions
      const instructionsRes = await fetch(
        setupBaseUrl("http", `integration/get_instructions`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token,
            db_name: apiKeyName,
          }),
        }
      );
      const instructionsData = await instructionsRes.json();
      // map instructions to compulsory glossary
      setCompulsoryGlossary(instructionsData.instructions);
      
      // get golden queries
      const goldenQueriesRes = await fetch(
        setupBaseUrl("http", `integration/get_golden_queries`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token,
            db_name: apiKeyName,
          }),
        }
      );
      const goldenQueriesData = await goldenQueriesRes.json();
      setGoldenQueries(goldenQueriesData.golden_queries);

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
      setupBaseUrl("http", `integration/update_instructions`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          instructions: compulsoryGlossary,
          token,
          db_name: apiKeyName,
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
            db_name: apiKeyName,
            golden_queries: goldenQueries,
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
            db_name: apiKeyName,
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

  const tabs = [
    {
      key: "text-to-sql-instructions",
      name: "Text-to-SQL",
      content: <Instructions
        title="Instructions"
        description="This the information about your data that the model considers when generating your SQL queries. Feel free to edit these instructions to get the best results."
        compulsoryGlossary={compulsoryGlossary}
        setCompulsoryGlossary={setCompulsoryGlossary}
        prunableGlossary={prunableGlossary}
        setPrunableGlossary={setPrunableGlossary}
        updateGlossary={updateGlossary}
        updateGlossaryLoadingFunction={setIsUpdatingInstructions}
        isLoading={isLoading}
        isUpdatingInstructions={isUpdatingInstructions}
      />,
    },
    {
      key: "golden-queries",
      name: "Golden Queries",
      content: <GoldenQueries
        token={token}
        apiKeyName={apiKeyName}
        goldenQueries={goldenQueries}
        setGoldenQueries={setGoldenQueries}
        updateMetadata={updateMetadata}
        updateMetadataLoadingFunction={setIsUpdatingGoldenQueries}
        isLoading={isLoading}
        isUpdatingGoldenQueries={isUpdatingGoldenQueries}
        setUpdatedGoldenQueriesToggle={setUpdatedGoldenQueriesToggle}
      />,
    },
    {
      key: "clarification-guidelines",
      name: "Clarifications",
      content: <Guidelines
        token={token}
        apiKeyName={apiKeyName}
        guidelineType={"clarification"}
      />,
    },
    {
      key: "generate-question-guidelines",
      name: "Question Generation",
      content: <Guidelines
        token={token}
        apiKeyName={apiKeyName}
        guidelineType={"generate_questions"}
      />,
    },
    {
      key: "generate-deeper-question-guidelines",
      name: "Question Generation (2)",
      content: <Guidelines
        token={token}
        apiKeyName={apiKeyName}
        guidelineType={"generate_questions_deeper"}
      />,
    },
    {
      key: "generate-report-guidelines",
      name: "Reports",
      content: <Guidelines
        token={token}
        apiKeyName={apiKeyName}
        guidelineType={"generate_report"}
      />,
    },
  ];

  return (
    <>
      <Meta />
      <Scaffolding id="align-model" userType="admin">
        {apiKeyNames.length > 1 ? (
          <div className="p-1 mt-1 w-full">
              <Select
                className="w-full"
                onChange={(e) => {
                  setApiKeyName(e);
                }}
                options={apiKeyNames.map((item) => {
                  return { value: item, key: item, label: item };
                })}
                value={apiKeyName}
              />
          </div>
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
          <Tabs
            size="large"
            tabs={tabs}
            defaultSelected="instructions"
          />
        </div>
      </Scaffolding>
    </>
  );
};

export default AlignModel;
