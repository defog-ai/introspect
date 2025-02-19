import { useState, useEffect, useContext } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import setupBaseUrl from "$utils/setupBaseUrl";
import Instructions from "../components/align-model/Instructions";
import GoldenQueries from "../components/align-model/GoldenQueries";
import Guidelines from "../components/align-model/Guidelines";
import { Settings } from "lucide-react";
import { MessageManagerContext, SingleSelect as Select, Tabs } from "@defogdotai/agents-ui-components/core-ui";

const AlignModel = () => {
  const [instructions, setInstructions] = useState("");
  const [goldenQueries, setGoldenQueries] = useState([]); // [ { question: "", sql: "" }, ... ]
  const [token, setToken] = useState("");

  // loading states
  const [isLoading, setIsLoading] = useState(false);
  const [isUpdatingInstructions, setIsUpdatingInstructions] = useState(false);
  const [isUpdatingGoldenQueries, setIsUpdatingGoldenQueries] = useState(false);
  const message = useContext(MessageManagerContext);
  const [apiKeyNames, setApiKeyNames] = useState([]);

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
    getGlossaryGoldenQueries();
  }, [apiKeyName]);

  const getGlossaryGoldenQueries = async () => {
    setIsLoading(true);
    const token = localStorage.getItem("defogToken");
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
      setInstructions(instructionsData.instructions);
      
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

  const updateInstructions = async (
    instructions,
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
          instructions: instructions,
          token,
          db_name: apiKeyName,
        }),
      }
    );
    const data = await res.json();
    setLoading(false);
    console.log(data);
    if (data.success === true) {
      message.success("Instructions updated successfully!");
    }
  };

  const updateGoldenQueries = async (question, sql) => {
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
            golden_queries: [
              {
                question: question,
                sql: sql,
              },
            ],
          }),
        }
      );

      const data = await res.json();
      setIsUpdatingGoldenQueries(false);
      if (data.success === true) {
        message.success("Golden queries updated successfully!");
      }
    }
  };

  const deleteGoldenQueries = async (question) => {
    if (!token || !apiKeyName) {
      message.error("Please log in to continue");
      return;
    }

    // check if user is sure that they want to delete golden query
    const isConfirmed = confirm("Are you sure you want to delete this golden query?");
    if (!isConfirmed) {
      return;
    }

    try {
      const response = await fetch(setupBaseUrl("http", `integration/delete_golden_queries`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
          db_name: apiKeyName,
          questions: [question]
        }),
      });

      if (!response.ok) {
        message.error("Failed to delete golden query");
      } else {
        message.success("Golden query deleted successfully");
      }

      const newGoldenQueries = [...goldenQueries];
      // get index of current question
      const index = newGoldenQueries.findIndex((gq) => gq.question === question);
      // remove current question
      newGoldenQueries.splice(index, 1);
      setGoldenQueries(newGoldenQueries);
    } catch (error) {
      console.error("Error deleting golden query:", error);
    }
  };

  const tabs = [
    {
      key: "text-to-sql-instructions",
      name: "Text-to-SQL",
      content: <Instructions
        title="Instructions"
        description="This the information about your data that the model considers when generating your SQL queries. Feel free to edit these instructions to get the best results."
        instructions={instructions}
        setInstructions={setInstructions}
        updateInstructions={updateInstructions}
        updateInstructionsLoadingFunction={setIsUpdatingInstructions}
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
        updateGoldenQueries={updateGoldenQueries}
        deleteGoldenQueries={deleteGoldenQueries}
        isLoading={isLoading}
        isUpdatingGoldenQueries={isUpdatingGoldenQueries}
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
            <Settings size={48} color="#1890ff" />{" "}
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
