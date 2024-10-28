import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import { Button, Col, Input, message, Upload, Select } from "antd";
import { useEffect, useRef, useState } from "react";
import {
  CloseCircleOutlined,
  InboxOutlined,
  MinusOutlined,
} from "@ant-design/icons";

import CodeMirror, { EditorView } from "@uiw/react-codemirror";
import { sql as codemirrorSql } from "@codemirror/lang-sql";
import { twMerge } from "tailwind-merge";

const { Dragger } = Upload;

interface RegressionItem {
  /**
   * This is the array of questions. If it's more than 1 question, all but the last one will be taken as "previous context" and will be testted as a follow on question.
   */
  questions: string[];
  /**
   * The correct SQL
   */
  sql: string;
}

/**
 * Contains all the regression items so far.
 */
type RegressionItems = RegressionItem[];

export default function TestRegressionPage() {
  const [apiKeyNames, setApiKeyNames] = useState([]);
  const [apiKeyName, setApiKeyName] = useState(null);

  const input = useRef(null);
  const editor = useRef(null);

  const [questions, setQuestions] = useState<RegressionItems>([
    {
      questions: ["Show me 5 rows", "Now show me stuff"],
      sql: "select *\nfrom all;",
    },
    {
      questions: ["Show me 51 rows", "filter them", "Now show me other stuff"],
      sql: "select *\nfrom all;",
    },
  ]);

  const [questionToBeAdded, setQuestionToBeAdded] = useState<RegressionItem>({
    questions: [],
    sql: "",
  });

  const getApiKeyNames = async (token) => {
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_api_key_names",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
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
  };

  const [token, setToken] = useState(null);

  const [filter, setFilter] = useState(""); // filter for search

  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const apiKeyName = localStorage.getItem("defogDbSelected");
    const token = localStorage.getItem("defogToken");
    getApiKeyNames(token);
    if (apiKeyName) {
      setApiKeyName(apiKeyName);
    } else {
      setApiKeyName(apiKeyNames[0]);
    }
    setToken(token);
  }, []);

  useEffect(() => {
    if (apiKeyName) {
      localStorage.setItem("defogDbSelected", apiKeyName);
    }
  }, [apiKeyName]);

  return (
    <div className="flex justify-center">
      <Meta />
      <Scaffolding id={"view-feedback"} userType={"admin"}>
        {apiKeyNames.length > 1 ? (
          <div>
            <Col span={24} style={{ paddingBottom: "1em" }}>
              <Select
                style={{ width: "100%" }}
                title="Select API Key"
                onChange={(e) => {
                  setApiKeyName(e);
                }}
                options={apiKeyNames.map((item) => {
                  return { value: item, key: item, label: item };
                })}
                value={apiKeyName}
              />
            </Col>
          </div>
        ) : null}

        <div className="flex flex-col gap-3">
          <div className="w-full bg-gray-50 rounded-md border">
            <div className="flex flex-row items-center border-b p-4">
              <h1 className="font-bold">Add a question</h1>
              <div className="grow text-right">
                <Button
                  type={"primary"}
                  onClick={() => {
                    if (
                      questionToBeAdded.questions.length === 0 &&
                      !input.current.input.value
                    ) {
                      message.error("Please add at least one question");
                      return;
                    }

                    if (
                      questionToBeAdded.questions.length === 0 &&
                      input.current.input.value
                    ) {
                      setQuestionToBeAdded({
                        ...questionToBeAdded,
                        questions: [input.current.input.value],
                      });
                      input.current.input.value = "";
                      return;
                    }

                    if (!questionToBeAdded.sql) {
                      message.error("Please add the SQL query");
                      return;
                    }

                    setQuestions([questionToBeAdded, ...questions]);

                    setQuestionToBeAdded({
                      questions: [],
                      sql: "",
                    });
                  }}
                >
                  Add
                </Button>
              </div>
            </div>
            <div className="py-4">
              <div className="grid grid-cols-10 text-gray-500 relative overflow-hidden px-4">
                <div className="line h-full top-5 w-0.5 left-7 absolute bottom-0 bg-gray-200"></div>

                <div className="col-span-4 relative flex flex-col gap-3">
                  {questionToBeAdded.questions.map((question, index) => {
                    return (
                      <div key={index} className="relative group">
                        <div className="flex flex-row items-center">
                          <CloseCircleOutlined
                            className="text-sm ml-1.5 mr-2 bg-gray-50 z-[2] group-hover:text-red hover:text-rose-500 cursor-pointer"
                            label="Delete"
                            onClick={() => {
                              const newQuestions = [
                                ...questionToBeAdded.questions,
                              ];
                              newQuestions.splice(index, 1);
                              setQuestionToBeAdded({
                                ...questionToBeAdded,
                                questions: newQuestions,
                              });
                            }}
                          ></CloseCircleOutlined>

                          {question}
                        </div>
                      </div>
                    );
                  })}

                  <div className="flex flex-row items-center group">
                    {/* <PlusCircleOutlined
                    className="text-sm ml-1.5 mr-2 bg-gray-50"
                    label="Add"
                  ></PlusCircleOutlined> */}
                    <div className="flex flex-col items-start gap-2 ml-7">
                      <span className="text-xs">
                        {questionToBeAdded.questions.length
                          ? "Type and press Enter to add a follow on question"
                          : "Type and press Enter to start adding a question"}
                      </span>
                      <Input
                        size="middle"
                        type="text"
                        placeholder="New question"
                        className="rounded-md border-gray-300 p-1 px-2"
                        ref={input}
                        onPressEnter={(e) => {
                          if (e.target.value === "") {
                            return;
                          }

                          setQuestionToBeAdded({
                            ...questionToBeAdded,
                            questions: [
                              ...questionToBeAdded.questions,
                              e.target.value,
                            ],
                          });

                          e.target.value = "";
                        }}
                      />
                    </div>
                  </div>
                </div>
                <div className="col-span-6 relative flex flex-col gap-2 pl-4">
                  <span className="text-xs">Type your SQL here</span>
                  <CodeMirror
                    className="border border-gray-300"
                    extensions={[codemirrorSql(), EditorView.lineWrapping]}
                    value={questionToBeAdded.sql}
                    basicSetup={{
                      lineNumbers: false,
                    }}
                    ref={editor}
                    editable={true}
                    onChange={(value) => {
                      setQuestionToBeAdded({
                        ...questionToBeAdded,
                        sql: value,
                      });
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="w-full text-left bg-gray-50 rounded-md border p-4">
            <Dragger
              name={"file"}
              showUploadList={false}
              accept=".json"
              onDrop={(e) => {
                const file = e.dataTransfer.files[0];
                if (file.type !== "application/json") {
                  message.error("Only JSON files accepted");
                  return;
                }

                // read the file as json, and
                // check that the format of this json matches the RegressionItem type
                const reader = new FileReader();

                reader.readAsText(file);

                reader.onload = async (e) => {
                  const result = e.target.result;

                  try {
                    const json = JSON.parse(result);
                    if (json instanceof Array) {
                      if (
                        json.every((item) => {
                          return (
                            item.questions instanceof Array &&
                            item.sql &&
                            typeof item.sql === "string"
                          );
                        })
                      ) {
                        setQuestions(json);
                      } else {
                        message.error(
                          "Invalid JSON format. The JSON should be an array, and each item must have a questions array and a sql string"
                        );
                      }
                    } else {
                      message.error("Could not upload JSON.");
                    }
                  } catch (e) {
                    message.error("Could not upload JSON.");
                  }
                };
              }}
            >
              <h1 className="font-bold mb-4">Or upload a JSON file</h1>
              <InboxOutlined className="text-4xl"></InboxOutlined>
            </Dragger>
          </div>

          <div className="bg-gray-50 rounded-md border">
            <div className="flex flex-row items-center mb-4 border-b p-4">
              <h1 className="font-bold">Added questions</h1>
              <div className="grow text-right">
                <Button
                  type={"primary"}
                  onClick={() => {
                    const element = document.createElement("a");
                    const file = new Blob(
                      [JSON.stringify(questions, null, 2)],
                      {
                        type: "application/json",
                      }
                    );
                    element.href = URL.createObjectURL(file);
                    element.download = "regression.json";
                    document.body.appendChild(element); // Required for this to work in FireFox
                    element.click();
                  }}
                >
                  Download JSON
                </Button>
              </div>
            </div>
            <div className="px-4">
              <Input
                className="rounded-md border-gray-300 w-40 p-1 px-2"
                size="small"
                type="text"
                placeholder="Filter questions"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
            </div>
            <div className="flex flex-col">
              {questions
                .filter((item) => {
                  return item.questions
                    .map((question) => {
                      return question
                        .toLowerCase()
                        .includes(filter.toLowerCase());
                    })
                    .some((item) => item);
                })
                .map((item, idx) => {
                  return (
                    <div
                      key={idx}
                      className="grid grid-cols-10 text-gray-500 relative even:bg-gray-100"
                    >
                      <div className="col-span-4 relative flex flex-col gap-4 border-r p-6">
                        <div className="line h-[80%] top-[10%] w-0.5 left-[1.85em] z-[1] absolute bottom-0 bg-gray-200"></div>
                        {item.questions.map((question, j) => {
                          return (
                            <div key={j} className="flex flex-row items-center">
                              <div>
                                <MinusOutlined
                                  className={twMerge(
                                    "relative text-xs mr-2 z-[2] bg-gray-100"
                                  )}
                                ></MinusOutlined>
                                {question}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <div className="col-span-6 p-4">
                        <CodeMirror
                          className="border border-gray-300"
                          extensions={[
                            codemirrorSql(),
                            EditorView.lineWrapping,
                          ]}
                          value={item.sql}
                          basicSetup={{
                            lineNumbers: false,
                          }}
                          ref={editor}
                          editable={false}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      </Scaffolding>
    </div>
  );
}
