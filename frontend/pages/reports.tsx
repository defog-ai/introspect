// @ts-nocheck
import { Button, SpinningLoader, TextArea, SingleSelect as Select, MultiSelect } from "@defogdotai/agents-ui-components/core-ui";
import { useState, useEffect, useCallback, useMemo } from "react";
import Sources from "../components/oracle/Sources";
import ReportStatus from "../components/oracle/ReportStatus";
import { X, Trash, FileText } from "lucide-react";
import setupBaseUrl from "$utils/setupBaseUrl";

// Types
type QueryTaskType = "exploration" | "";

interface Report {
  id: string;
  report_name: string;
  report_id: string;
  status: "pending" | "done" | "error";
  date_created: string;
  question: string;
  inputs?: {
    user_question?: string;
    [key: string]: any;
  };
  key_name?: string;
  task_type?: QueryTaskType;
  clarifications?: ClarificationObject[];
  sources?: string[];
  error?: string;
}

interface ClarificationObject {
  clarification: string;
  options: string[];
  input_type: "single_choice" | "multiple_choice" | "text";
  is_answered?: boolean;
  answer?: string | string[];
}

// Custom hook for API operations
const useOracleApi = (token: string | undefined, apiKeyName: string) => {
  const fetchReports = useCallback(async () => {
    if (!token) return null;
    try {
      const res = await fetch(setupBaseUrl("http", "oracle/list_reports"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, key_name: apiKeyName }),
      });
      if (!res.ok) throw new Error("Failed to fetch reports");
      const data = await res.json();
      return data.reports;
    } catch (error) {
      console.error("Error fetching reports:", error);
      return null;
    }
  }, [token, apiKeyName]);

  const deleteReport = async (reportId: string) => {
    if (!token) return false;
    try {
      const res = await fetch(setupBaseUrl("http", "oracle/delete_report"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          key_name: apiKeyName,
          report_id: reportId,
          token,
        }),
      });
      return res.ok;
    } catch (error) {
      console.error("Error deleting report:", error);
      return false;
    }
  };

  const getClarifications = async (userQuestion: string) => {
    if (!token) return null;
    try {
      const res = await fetch(setupBaseUrl("http", "oracle/clarify_question"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          key_name: apiKeyName,
          token,
          user_question: userQuestion,
          task_type: "exploration",
          answered_clarifications: [],
        }),
      });
      if (!res.ok) throw new Error("Failed to get clarifications");
      const data = await res.json();
      return data.clarifications;
    } catch (error) {
      console.error("Error getting clarifications:", error);
      return null;
    }
  };

  const generateReport = async (userQuestion: string, sources: any[], clarifications: ClarificationObject[]) => {
    if (!token) return false;
    try {
      const selectedSourceLinks = sources
        .filter((source) => source.selected)
        .map((source) => source.link);

      const res = await fetch(setupBaseUrl("http", "oracle/begin_generation"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          key_name: apiKeyName,
          token,
          user_question: userQuestion,
          sources: selectedSourceLinks,
          task_type: "exploration",
          clarifications: clarifications.filter((c) => c.answer),
        }),
      });
      return res.ok;
    } catch (error) {
      console.error("Error generating report:", error);
      return false;
    }
  };

  return { fetchReports, deleteReport, getClarifications, generateReport };
};

// Utility Components
const ReportDateTime = ({ date }: { date: string }) => {
  // Parse the date and adjust for local timezone
  const localDate = new Date(date + 'Z');  // Append Z to treat the input as UTC
  
  return (
    <div className="text-gray-400 dark:text-gray-500 flex items-center space-x-2">
      <span>
        {localDate.toLocaleDateString("en-GB", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        })}
      </span>
      <span className="text-gray-300 dark:text-gray-600">•</span>
      <span>
        {localDate.toLocaleTimeString("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        })}
      </span>
    </div>
  );
};

// Main Component
function OracleDashboard() {
  // Authentication state
  const [token, setToken] = useState<string>(null);
  const [apiKeyName, setApiKeyName] = useState<string>("");
  const [apiKeyNames, setApiKeyNames] = useState<string[]>([]);

  // Report generation state
  const [userQuestion, setUserQuestion] = useState("");
  const [sources, setSources] = useState<string[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [isPolling, setIsPolling] = useState(false);

  // Clarification state
  const [clarifications, setClarifications] = useState<ClarificationObject[]>([]);
  const [hasClarified, setHasClarified] = useState(false);
  const [loadingClarifications, setLoadingClarifications] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);

  // Initialize API hooks
  const api = useOracleApi(token, apiKeyName);

  // Memoize API functions to prevent unnecessary re-renders
  const fetchReports = useMemo(() => api.fetchReports, [api]);
  const deleteReport = useMemo(() => api.deleteReport, [api]);
  const getClarifications = useMemo(() => api.getClarifications, [api]);
  const generateReport = useMemo(() => api.generateReport, [api]);

  const updateToken = useEffect(() => {
    const token = localStorage.getItem("defogToken");
    if (token) setToken(token);
  }, []);

  const getApiKeyNames = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(
        (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_api_key_names",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        }
      );
      if (!res.ok) throw new Error("Failed to get API key names");
      const data = await res.json();
      setApiKeyNames(data.api_key_names);
      setApiKeyName(data.api_key_names[0]);
    } catch (error) {
      console.error("Failed to get API key names:", error);
    }
  }, [token]);

  // Initial setup and fetch
  const fetchInitialReports = useCallback(async () => {
    if (!token || !apiKeyName) return;
    console.log("Initial fetch starting");
    try {
      const reports = await fetchReports();
      if (reports) {
        console.log("Initial fetch complete:", reports.length, "reports");
        setReports(reports);
      }
    } catch (error) {
      console.error("Initial fetch error:", error);
    }
  }, [token, apiKeyName, fetchReports]);

  useEffect(() => {
    getApiKeyNames();
  }, [getApiKeyNames]);

  useEffect(() => {
    fetchInitialReports();
  }, [fetchInitialReports]);

  // Polling logic
  useEffect(() => {
    if (!isPolling) {
      return;
    }

    console.log("Setting up polling");
    const intervalId = setInterval(async () => {
      try {
        console.log("Polling for reports...");
        const reports = await fetchReports();
        
        if (reports) {
          console.log("Poll complete:", reports.length, "reports");
          setReports(reports);
          
          // Check if all reports are done
          const allDone = reports.every(r => r.status === "done" || r.status === "error");
          console.log("All reports done:", allDone);
          
          if (allDone) {
            console.log("Stopping polling - all reports done");
            setIsPolling(false);
          }
        }
      } catch (error) {
        console.error("Polling error:", error);
        setIsPolling(false);
      }
    }, 1000);

    return () => {
      console.log("Cleaning up polling interval");
      clearInterval(intervalId);
    };
  }, [isPolling, fetchReports]);

  // Clarification handlers
  const handleClarificationAnswer = useCallback((index: number, answer: string | string[]) => {
    setClarifications((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], is_answered: true, answer };
      return updated;
    });
  }, []);

  const handleClarificationDismiss = useCallback((index: number) => {
    setClarifications((prev) => {
      const updated = [...prev];
      updated.splice(index, 1);
      return updated;
    });
  }, []);

  const getClarificationOptions = useCallback((options: string[]) => 
    options.map(opt => ({ value: opt, key: opt, label: opt })), 
  []);

  // Action handlers
  const handleQuestionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setUserQuestion(e.target.value);
  };

  const handleGetClarifications = async () => {
    setHasClarified(true);
    setLoadingClarifications(true);
    const clarifications = await getClarifications(userQuestion);
    if (clarifications) {
      setClarifications(clarifications);
    }
    setLoadingClarifications(false);
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    const success = await generateReport(userQuestion, sources, clarifications);
    if (success) {
      console.log("Report generation successful, starting polling");
      setIsPolling(true);
    }
    setGeneratingReport(false);
  };

  const handleDeleteReport = async (reportId: string) => {
    const success = await deleteReport(reportId);
    if (success) {
      const reports = await fetchReports();
      if (reports) setReports(reports);
    }
  };

  return (
    <>
      {apiKeyNames.length > 1 && (
        <div className="flex">
          <Select
            rootClassNames="w-full"
            onChange={setApiKeyName}
            options={apiKeyNames.map((item) => ({
              value: item,
              key: item,
              label: item,
            }))}
            value={apiKeyName}
          />
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold mb-2 dark:text-gray-200">
            Generate Report
          </h1>
        </div>

        <div className="relative mb-6">
          <TextArea
            placeholder="Describe what you would like a report for..."
            value={userQuestion}
            onChange={handleQuestionChange}
            defaultRows={1}
            disabled={generatingReport || loadingClarifications}
            onKeyDown={(e: React.KeyboardEvent) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (hasClarified === true) {
                  handleGenerateReport();
                } else {
                  handleGetClarifications();
                }
              }
            }}
          />
        </div>

        <div className="mt-6">
          <Sources sources={sources} setSources={setSources} />
        </div>

        {hasClarified && (
          <div className="mt-4">
            {loadingClarifications ? (
              <div>
                <SpinningLoader /> Generating Clarifying Questions...
              </div>
            ) : (
              <div>
                <h2 className="text-lg font-semibold mb-2 dark:text-gray-200">
                  Clarifications
                </h2>
                <div className="space-y-2">
                  {clarifications.map((clarification, index) => (
                    <div
                      key={index}
                      className="bg-gray-50 dark:bg-gray-800 rounded p-2"
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex justify-between items-start">
                          <div className="text-sm text-gray-700 dark:text-gray-300">
                            {clarification.clarification}
                          </div>
                          <button
                            onClick={() => handleClarificationDismiss(index)}
                            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors ml-2"
                            title="Dismiss this clarification"
                          >
                            <X size={14} />
                          </button>
                        </div>
                        {clarification.input_type === "text" && (
                          <TextArea
                            placeholder="Type your answer here..."
                            value={clarification.answer as string || ""}
                            onChange={(e) =>
                              handleClarificationAnswer(index, e.target.value)
                            }
                            defaultRows={1}
                          />
                        )}
                        {clarification.input_type === "single_choice" && (
                          <Select
                            options={getClarificationOptions(clarification.options)}
                            value={clarification.answer as string || ""}
                            onChange={(value) =>
                              handleClarificationAnswer(index, value)
                            }
                          />
                        )}
                        {clarification.input_type === "multiple_choice" && (
                          <MultiSelect
                            style={{ width: "100%" }}
                            options={getClarificationOptions(clarification.options)}
                            value={clarification.answer as string[] || []}
                            onChange={(value) =>
                              handleClarificationAnswer(index, value)
                            }
                          />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <Button
          id="generate-report-button"
          className="px-4 py-2 my-2 rounded-lg"
          onClick={hasClarified ? handleGenerateReport : handleGetClarifications}
          disabled={loadingClarifications || generatingReport || userQuestion.length < 1}
        >
          {hasClarified ? "Generate Report" : "Initialize Report"}
        </Button>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg max-w-4xl mx-auto mt-8">
        <h2 className="text-2xl font-semibold mb-4 dark:text-gray-200">
          Past Reports
        </h2>
        {reports.map((report, index) => (
          <div
            key={index}
            className="bg-purple-100 dark:bg-purple-900/30 shadow-lg rounded-lg mb-4 overflow-hidden border border-purple-200 dark:border-purple-800 hover:border-purple-300 dark:hover:border-purple-700 transition-all"
          >
            <div className="p-4">
              {report.report_name ? (
                <>
                  <h3 className="text-lg font-semibold text-purple-700 dark:text-purple-400 mb-1">
                    {report.report_name}
                  </h3>
                  <div className="text-base mb-3 flex items-center justify-between">
                    <div className="text-gray-500 dark:text-gray-400 flex items-center">
                      <FileText className="mr-1" />
                      <span>{String(report.report_id).padStart(3, "0")}</span>
                    </div>
                    <ReportDateTime date={report.date_created} />
                  </div>
                </>
              ) : (
                <div className="mb-3">
                  <div className="text-base flex items-center justify-between">
                    <div className="text-gray-700 dark:text-gray-300 font-semibold flex items-center">
                      <FileText className="mr-2" />
                      <span>{report?.inputs?.user_question}</span>
                    </div>
                    <ReportDateTime date={report.date_created} />
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <ReportStatus status={report.status} />
                </div>
                <div className="flex items-center space-x-2">
                  {report.status === "done" && (
                    <Button
                      className="text-purple-700 hover:text-purple-900 dark:text-purple-400 dark:hover:text-purple-300"
                      onClick={() =>
                        window.open(
                          `/view-report?reportId=${report.report_id}&keyName=${apiKeyName}`,
                          "_blank"
                        )
                      }
                    >
                      View Report
                    </Button>
                  )}
                  <Button
                    className="text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400 transition-colors"
                    onClick={() => handleDeleteReport(report.report_id)}
                  >
                    <Trash />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

export default OracleDashboard;