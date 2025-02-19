import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import { useCallback, useContext, useEffect, useMemo, useState } from "react";
import { CheckCircle, XCircle } from "lucide-react";
import CodeMirror, { EditorView } from "@uiw/react-codemirror";
import { sql as codemirrorSql } from "@codemirror/lang-sql";
import setupBaseUrl from "$utils/setupBaseUrl";

import {
  DropFiles,
  SingleSelect,
  Input as DefogInput,
  Button,
  SpinningLoader,
  MessageManagerContext,
} from "@defogdotai/agents-ui-components/core-ui";

interface ValidationResult {
  correct: boolean;
  model_sql: string;
}

interface RegressionItem {
  questions: string[];
  sql: string;
  id: string;
  validationResult?: ValidationResult;
}

type RegressionItems = RegressionItem[];

export default function TestRegressionPage() {
  const [apiKeyNames, setApiKeyNames] = useState<string[]>([]);
  const [apiKeyName, setApiKeyName] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const [queries, setQueries] = useState<RegressionItems>([]);
  const [questionToBeAdded, setQuestionToBeAdded] = useState<RegressionItem>({
    questions: [],
    sql: "",
    id: crypto.randomUUID(),
  });

  const [inputVal, setInputVal] = useState("");
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState<string | boolean>(false);

  const message = useContext(MessageManagerContext);

  const previousQuestions = useMemo(
    () => questionToBeAdded.questions.slice(0, -1),
    [questionToBeAdded.questions]
  );
  const mainQuestion = useMemo(
    () => questionToBeAdded.questions.slice(-1),
    [questionToBeAdded.questions]
  );

  // Fetch the list of DB names
  const getApiKeyNames = async (token: string) => {
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_db_names",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      }
    );
    if (!res.ok) {
      throw new Error("Failed to get api key names. Check your network?");
    }
    const data = await res.json();
    setApiKeyNames(data.db_names || []);
  };

  useEffect(() => {
    const localToken = localStorage.getItem("defogToken");
    setToken(localToken);

    if (localToken) {
      getApiKeyNames(localToken);
    }
    const storedApiKeyName = localStorage.getItem("defogDbSelected");
    if (storedApiKeyName) {
      setApiKeyName(storedApiKeyName);
    }
  }, []);

  useEffect(() => {
    if (apiKeyName) {
      localStorage.setItem("defogDbSelected", apiKeyName);
    }
  }, [apiKeyName]);

  // POST to readiness/regression_results
  const getRegressionResults = useCallback(
    async (query: RegressionItem | null = null) => {
      try {
        setLoading(query ? query.id : "all");
        const res = await fetch(
          setupBaseUrl("http", `readiness/regression_results`),
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              token,
              key_name: apiKeyName,
              queries: query ? [query] : queries,
            }),
          }
        );
        const data = await res.json();
        const queryWiseResults = data.query_wise_results || {};

        // Update each item with its validationResult
        setQueries((prev) =>
          prev.map((item) => ({
            ...item,
            validationResult: queryWiseResults[item.id] ?? item.validationResult,
          }))
        );
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    },
    [queries, apiKeyName, token]
  );

  // Handle dropping a JSON file
  const handleFilesDropped = (files: FileList) => {
    if (!files?.length) return;
    const file = files[0];
    if (file.type !== "application/json") {
      message.error("Only JSON files accepted");
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e?.target?.result;
      if (!result) return;
      try {
        const json = JSON.parse(result.toString());
        if (Array.isArray(json)) {
          const validStructure = json.every((item: any) => {
            return Array.isArray(item.questions) && typeof item.sql === "string";
          });
          if (!validStructure) {
            message.error(
              "Invalid JSON format. Must be array of { questions[], sql: string }"
            );
            return;
          }
          json.forEach((item: any) => {
            item.id = crypto.randomUUID();
            item.validationResult = item.validationResult || null;
          });
          setQueries(json);
          message.success("JSON uploaded successfully");
        } else {
          message.error("Could not upload JSON (expected an array).");
        }
      } catch (err) {
        console.error(err);
        message.error("Could not parse JSON file.");
      }
    };
    reader.readAsText(file);
  };

  // Add the new question + SQL
  const handleAddQuestion = () => {
    // If user typed a single question but never pressed Enter
    if (!questionToBeAdded.questions.length && inputVal) {
      questionToBeAdded.questions.push(inputVal);
      setInputVal("");
    }
    if (!questionToBeAdded.questions.length) {
      message.error("Please add at least one question");
      return;
    }
    if (!questionToBeAdded.sql) {
      message.error("Please add the SQL query");
      return;
    }
    setQueries([
      {
        ...questionToBeAdded,
        id: crypto.randomUUID(),
        validationResult: null,
      },
      ...queries,
    ]);
    // Reset
    setQuestionToBeAdded({ questions: [], sql: "", id: crypto.randomUUID() });
  };

  return (
    <div className="flex justify-center">
      <Meta />
      <Scaffolding id="view-feedback" userType="admin">
        {/* If multiple DB names, show SingleSelect */}
        {apiKeyNames.length > 1 && (
          <div className="mb-4 w-full">
            <SingleSelect
              placeholder="Select API Key"
              rootClassNames="w-full"
              options={apiKeyNames.map((item) => ({
                value: item,
                label: item,
              }))}
              value={apiKeyName || undefined}
              onChange={(val) => setApiKeyName(val)}
            />
          </div>
        )}

        <div className="flex flex-col gap-3 mb-4">
          {/* "Upload or Add a question" section */}
          <div className="grid grid-cols-4 md:grid-cols-12 w-full bg-gray-50 rounded-md border gap-2 divide-x">
            {/* Drag/Drop JSON area */}
            <div className="col-span-4 p-4 flex flex-col items-center justify-center">
              <input
                type="file"
                accept=".json"
                className="hidden"
                id="file-upload"
                onChange={(e) => handleFilesDropped(e.target.files)}
              />
              <DropFiles
                allowMultiple={false}
                acceptedFileTypes={[".json"]}
                onDrop={(e) => {
                  const files = e.dataTransfer.files;
                  handleFilesDropped(files);
                }}
              >
                <label
                  htmlFor="file-upload"
                  className="w-full cursor-pointer"
                >
                  <div className="flex flex-col items-center justify-center p-6 text-center border border-dashed border-gray-300 rounded-md hover:bg-gray-100 transition-colors">
                    <div className="text-4xl mb-2">🗂️</div>
                    <h1 className="font-bold text-sm mb-2">Upload a JSON file</h1>
                    <p>Click or drag files to this area to upload</p>
                  </div>
                </label>
              </DropFiles>
            </div>

            {/* Manual add question area */}
            <div className="col-span-8 border-l">
              {/** 
               *  1) Make a row with "Or add a question manually" on left 
               *     and an "Add" button on right 
               */}
              <div className="flex items-center border-b p-4 justify-between">
                <h1 className="text-sm font-bold text-gray-800">
                  Or add a question manually
                </h1>
                <Button variant="primary" onClick={handleAddQuestion}>
                  Add
                </Button>
              </div>

              <div className="py-4">
                <div className="grid grid-cols-10 px-4 gap-3">
                  {/* Left side: questions */}
                  <div className="col-span-4 flex flex-col p-4 border-r">
                    <div className="previous-questions relative">
                      {previousQuestions.length > 0 && (
                        <div className="absolute z-[2] top-0 -left-2 w-1 h-full border border-r-0 border-gray-300"></div>
                      )}
                      {previousQuestions.map((question, index) => (
                        <div
                          key={index}
                          className="relative group text-sm mb-1"
                        >
                          <div className="flex flex-row items-center">
                            {question}
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="main-question mt-2">
                      {mainQuestion.map((question, index) => (
                        <div
                          key={index}
                          className="relative group text-lg font-semibold mb-4"
                        >
                          <div className="flex flex-row items-center">
                            {question}
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="flex flex-col text-gray-500">
                      <span className="text-sm mb-2">
                        {questionToBeAdded.questions.length
                          ? "Keep typing to add follow-up questions"
                          : "Type + press Enter to add a question"}
                      </span>
                      <DefogInput
                        placeholder="New question"
                        value={inputVal}
                        onChange={(e) => setInputVal(e.target.value)}
                        inputClassNames="rounded-md p-1 px-2 border-gray-300"
                        onPressEnter={(e) => {
                          if (inputVal) {
                            setQuestionToBeAdded((prev) => ({
                              ...prev,
                              questions: [...prev.questions, inputVal],
                            }));
                            setInputVal("");
                          }
                        }}
                      />
                    </div>
                  </div>

                  {/* Right side: SQL editor */}
                  <div className="col-span-6 flex flex-col gap-2 p-4">
                    <span className="text-sm text-gray-500">
                      Enter the correct SQL for the final question here
                    </span>
                    <CodeMirror
                      className="border border-gray-300"
                      extensions={[codemirrorSql(), EditorView.lineWrapping]}
                      value={questionToBeAdded.sql}
                      basicSetup={{ lineNumbers: false }}
                      editable={true}
                      onChange={(value) => {
                        setQuestionToBeAdded((prev) => ({
                          ...prev,
                          sql: value,
                        }));
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className="h-10 w-full flex items-center">
            <div className="h-0.5 w-full bg-gray-300"></div>
          </div>

          {/* Section with "Validate All" + "Download JSON" */}
          <div className="bg-gray-50 rounded-md border">
            {/** 
             * 2) Another row with "Added questions" on the left 
             *    and "Download JSON" + "Validate All" on the right 
             */}
            <div className="flex items-center border-b p-4 justify-between">
              <h1 className="text-sm font-bold text-gray-800">
                Added questions
              </h1>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => {
                    const blob = new Blob(
                      [JSON.stringify(queries, null, 2)],
                      { type: "application/json" }
                    );
                    const url = URL.createObjectURL(blob);
                    const element = document.createElement("a");
                    element.href = url;
                    element.download = "regression.json";
                    document.body.appendChild(element);
                    element.click();
                    document.body.removeChild(element);
                  }}
                >
                  Download JSON
                </Button>

                <Button
                  variant="primary"
                  disabled={!queries.length || !!loading}
                  onClick={() => getRegressionResults(null)}
                >
                  {loading === "all" && (
                    <SpinningLoader classNames="text-white w-4 h-4 mr-2 inline" />
                  )}
                  Validate All
                </Button>
              </div>
            </div>

            {/* If no queries */}
            {!queries.length && (
              <div className="p-4 text-gray-500">
                Please add questions above or upload a JSON file.
              </div>
            )}

            {/* If queries exist */}
            {queries.length > 0 && (
              <>
                <div className="px-4 my-4">
                  <DefogInput
                    placeholder="Filter questions"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    size="small"
                    inputClassNames="rounded-md border-gray-300 w-40 p-1 px-2"
                  />
                </div>

                {/* Table-ish header */}
                <div className="flex flex-col">
                  <div className="grid grid-cols-12 relative even:bg-gray-100 text-sm font-bold border-b">
                    <div className="col-span-2 p-4 border-r">Question</div>
                    <div className="col-span-4 p-4 border-r">Provided SQL</div>
                    <div className="col-span-4 p-4 border-r">Model SQL</div>
                    <div className="col-span-2 p-4">Result</div>
                  </div>

                  {queries
                    .filter((item) =>
                      item.questions.some((q) =>
                        q.toLowerCase().includes(filter.toLowerCase())
                      )
                    )
                    .map((item) => {
                      const previousQs = item.questions.slice(0, -1);
                      const mainQ = item.questions.slice(-1);

                      return (
                        <div
                          key={item.id}
                          className="grid grid-cols-12 relative even:bg-gray-100"
                        >
                          {/* 1) question column */}
                          <div className="col-span-2 flex flex-col px-6 py-4 border-r">
                            {previousQs.length > 0 && (
                              <div className="absolute z-[2] top-0 -left-2 w-1 h-full border border-r-0 border-gray-300"></div>
                            )}
                            {previousQs.map((question, i) => (
                              <div
                                key={i}
                                className="relative group text-sm mb-1"
                              >
                                {question}
                              </div>
                            ))}
                            {mainQ.map((question, i) => (
                              <div
                                key={i}
                                className="relative group text-lg font-semibold mb-4 mt-2"
                              >
                                {question}
                              </div>
                            ))}
                          </div>

                          {/* 2) Provided SQL */}
                          <div className="col-span-4 border-r p-4">
                            <CodeMirror
                              className="border border-gray-300"
                              extensions={[
                                codemirrorSql(),
                                EditorView.lineWrapping,
                              ]}
                              value={item.sql}
                              basicSetup={{ lineNumbers: false }}
                              editable={false}
                            />
                          </div>

                          {/* 3) Model SQL */}
                          <div className="col-span-4 border-r p-4">
                            {item.validationResult?.model_sql ? (
                              <CodeMirror
                                className="border border-gray-300"
                                extensions={[
                                  codemirrorSql(),
                                  EditorView.lineWrapping,
                                ]}
                                value={item.validationResult.model_sql}
                                basicSetup={{ lineNumbers: false }}
                                editable={false}
                              />
                            ) : null}
                          </div>

                          {/* 4) Result col + "Validate" button */}
                          <div className="col-span-2 p-4">
                            {loading !== item.id &&
                              item.validationResult &&
                              (item.validationResult.correct ? (
                                <div className="text-green-600 font-semibold mb-2">
                                  <CheckCircle className="mr-2" />
                                  Correct!
                                </div>
                              ) : (
                                <div className="text-red-600 font-semibold mb-2">
                                  <XCircle className="mr-2" />
                                  Incorrect!
                                </div>
                              ))}
                            <Button
                              variant="secondary"
                              onClick={() => getRegressionResults(item)}
                              disabled={!!loading && loading !== item.id}
                              className="mt-2"
                            >
                              {loading === item.id && (
                                <SpinningLoader classNames="inline w-4 h-4 mr-2 text-blue-600" />
                              )}
                              {item.validationResult ? "Re-validate" : "Validate"}
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </>
            )}
          </div>
        </div>
      </Scaffolding>
    </div>
  );
}
