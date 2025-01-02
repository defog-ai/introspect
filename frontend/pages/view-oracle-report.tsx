"use client";
import setupBaseUrl from "$components/oracle/setupBaseUrl";
import { useCallback, useContext, useEffect, useRef, useState } from "react";
import {
  Button,
  Modal,
  SpinningLoader,
  MessageManagerContext,
  TextArea,
} from "@defogdotai/agents-ui-components/core-ui";
import {
  getReportMDX,
  getReportFeedback,
  getReportAnalysisIds,
  getReportExecutiveSummary,
  extensions,
  parseMDX,
} from "$components/oracle/oracleUtils";

import { EditorProvider } from "@tiptap/react";
import React from "react";
import {
  OracleReportContext,
  Summary,
} from "$components/oracle/OracleReportContext";
import { ArrowLeft } from "lucide-react";
import { OracleBubbleMenu } from "$components/oracle/reports/OracleBubbleMenu";

export default function ViewOracleReport() {
  const [keyName, setKeyName] = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setKeyName(params.get("keyName"));
    setReportId(params.get("reportId"));
  }, []);

  const [tables, setTables] = useState<any>({});
  const [multiTables, setMultiTables] = useState<any>({});
  const [images, setImages] = useState<any>({});
  const [analysisIds, setAnalysisIds] = useState<string[]>([]);

  const message = useContext(MessageManagerContext);
  const feedbackTextArea = useRef<HTMLTextAreaElement>(null);

  const [mdx, setMDX] = useState<string | null>(null);
  const [executiveSummary, setExecutiveSummary] = useState<Summary | null>(
    null
  );

  const [currentFeedback, setCurrentFeedback] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  const [feedbackModalOpen, setFeedbackModalOpen] = useState<boolean>(false);

  const [analysisDrawerOpen, setAnalysisDrawerOpen] = useState<boolean>(false);

  const [drawerSelectedAnalysisId, setDrawerSelectedAnalysisId] = useState<
    string | null
  >(null);

  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const setup = async (reportId: string, keyName: string) => {
      try {
        setLoading(true);
        const token = localStorage.getItem("defogToken");
        const mdx = await getReportMDX(reportId, keyName, token);

        if (!mdx) {
          throw Error();
        }

        const parsed = parseMDX(mdx);

        setTables(parsed.tables);
        setImages(parsed.images);
        setMultiTables(parsed.multiTables);
        const feedback = await getReportFeedback(reportId, keyName, token);
        setCurrentFeedback(feedback || undefined);
        const sum: Summary = await getReportExecutiveSummary(
          reportId,
          keyName,
          token
        );

        // add ids to each recommendation
        sum.recommendations = sum.recommendations.map((rec) => ({
          id: crypto.randomUUID(),
          ...rec,
        }));

        setExecutiveSummary(sum);

        const analysisIds = await getReportAnalysisIds(
          reportId,
          keyName,
          token
        );

        setAnalysisIds(analysisIds);

        setMDX(parsed.mdx);
      } catch (e) {
        console.error(e);
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    if (reportId && keyName) {
      setup(reportId, keyName);
    }
  }, [reportId, keyName]);

  const submitFeedback = useCallback(async () => {
    if (!feedbackTextArea.current || !feedbackTextArea.current.value) {
      message.info("Feedback cannot be empty");
      return;
    }

    await fetch(setupBaseUrl("http", `oracle/feedback_report`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        report_id: reportId,
        key_name: keyName,
        feedback: feedbackTextArea.current.value,
      }),
    })
      .then(async (res) => {
        if (!res.ok) {
          throw Error(await res.text());
        }
        message.success("Feedback submitted");

        setFeedbackModalOpen(false);
      })
      .catch((e) => {
        console.error(e);
        message.error("Could not submit feedback");
      });
  }, [message, reportId, keyName]);

  if (loading) {
    return (
      <div
        className={
          "w-full h-full min-h-60 flex flex-col justify-center items-center text-center rounded-md p-2"
        }
      >
        <div className="mb-2 text-sm text-gray-400 dark:text-gray-200">
          <SpinningLoader classNames="w-5 h-5" />
          Loading
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={
          "w-full h-full min-h-60 flex flex-col justify-center items-center bg-rose-100 dark:bg-rose-900 text-red text-center rounded-md p-2"
        }
      >
        <div className="mb-2 text-sm text-rose-500 dark:text-rose-400">
          {error}
        </div>
      </div>
    );
  }

  if (!mdx) {
    return (
      <div
        className={
          "w-full h-full min-h-60 flex flex-col justify-center items-center"
        }
      >
        <div className="mb-2 text-sm text-gray-400 dark:text-gray-500">
          Fetching
        </div>
        <SpinningLoader classNames="w-5 h-5 text-gray-500 dark:text-gray-400" />
      </div>
    );
  }

  return (
    <OracleReportContext.Provider
      value={{
        tables: tables,
        multiTables: multiTables,
        images: images,
        analysisIds: analysisIds,
        executiveSummary: executiveSummary,
        reportId: reportId,
        keyName: keyName,
      }}
    >
      <div className="relative">
        <div className="flex flex-row fixed min-h-12 bottom-0 w-full bg-gray-50 dark:bg-gray-800 md:bg-transparent dark:md:bg-transparent md:w-auto md:sticky md:top-0 p-2 z-10 md:h-0">
          {/* @ts-ignore */}
          <Button
            onClick={() => window.location.replace("/oracle-frontend")}
            className="bg-transparent border-none hover:bg-transparent text-gray-700 dark:text-gray-300"
          >
            <ArrowLeft className="w-2" /> All reports
          </Button>
          <div className="flex flex-row gap-2 ml-auto">
            {/* @ts-ignore */}
            {/* <Button
              onClick={() => setAnalysisDrawerOpen(true)}
              className="ml-auto text-gray-700 dark:text-gray-300"
            >
              View analyses
            </Button> */}
            {/* @ts-ignore */}
            <Button
              onClick={() => setFeedbackModalOpen(true)}
              className="ml-auto text-gray-700 dark:text-gray-300"
            >
              Give feedback
            </Button>
          </div>

          <Modal
            rootClassNames="w-96 z-10"
            open={feedbackModalOpen}
            onOk={submitFeedback}
            onCancel={() => setFeedbackModalOpen(false)}
            title="Write your feedback and press submit"
            okText="Submit"
            className="dark:bg-gray-800 dark:text-gray-200"
          >
            <TextArea
              autoResize={true}
              ref={feedbackTextArea}
              defaultValue={currentFeedback}
            ></TextArea>
          </Modal>
        </div>
        <EditorProvider
          extensions={extensions}
          content={
            mdx.indexOf("<oracle-comment-handler />") > -1
              ? mdx
              : mdx + "<oracle-comment-handler />"
          }
          immediatelyRender={false}
          slotAfter
          editable={false}
          editorProps={{
            attributes: {
              class:
                "oracle-report-tiptap relative prose prose-base dark:prose-invert mx-auto p-2 mb-12 md:mb-0 focus:outline-none *:cursor-default",
            },
            // prosemirror has an issue where onselectionchange is not fired on uneditable editors
            // https://discuss.prosemirror.net/t/unexpected-selection-behavior-on-mouse-click-within-and-outside-an-existing-selection/5750/11
            // https://github.com/ueberdosis/tiptap/issues/4478
            // i don't know how windsurf figured this out, but it did.
            handleClick: (view, pos) => {
              const { state } = view;
              const { from, to } = state.selection;

              // If there's a selection and we clicked within it
              if (from !== to && pos >= from && pos <= to) {
                // Create empty selection at click position
                const tr = state.tr.setSelection(
                  state.selection.constructor.create(state.doc, pos, pos)
                );
                view.dispatch(tr);
              }
              return true;
            },
          }}
        >
          <OracleBubbleMenu keyName={keyName} reportId={reportId} />
        </EditorProvider>
        {/* <Drawer
          open={analysisDrawerOpen}
          onClose={() => setAnalysisDrawerOpen(false)}
          placement="bottom"
          size="large"
          title="Analyses"
        >
          <div className="z-10 w-1/4 p-4 md:gap-4 max-h-full overflow-scroll inline-block">
            <Select
              options={Object.values(analyses)
                .map((a) => {
                  return {
                    label: a.analysis_json.title,
                    value: a.analysis_id,
                  };
                })
                .concat([
                  {
                    label: "New",
                    value: null,
                  },
                ])}
              value={drawerSelectedAnalysisId}
              onChange={(value) => setDrawerSelectedAnalysisId(value)}
              className="md:hidden"
            />
            <div className="hidden md:block dark:bg-gray-800 dark:text-gray-200 space-y-4 bg-white h-20 md:h-auto max-w-full overflow-x-scroll">
              <div
                className={twMerge(
                  "rounded-md border inline-block md:block md:drop-shadow-md bg-white p-4 overflow-hidden cursor-pointer hover:border-gray-500 transition-all",
                  drawerSelectedAnalysisId === null
                    ? "border-gray-500"
                    : "border-gray-300"
                )}
                onClick={() => setDrawerSelectedAnalysisId(null)}
              >
                New
              </div>

              {Object.values(analyses).map((analysis) => (
                <div
                  className={twMerge(
                    "rounded-md border inline-block md:block md:drop-shadow-md bg-white p-4 overflow-hidden cursor-pointer hover:border-gray-500 transition-all",
                    drawerSelectedAnalysisId === analysis.analysis_id
                      ? "border-gray-500"
                      : "border-gray-300"
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    setDrawerSelectedAnalysisId((prev) =>
                      prev === analysis.analysis_id
                        ? null
                        : analysis.analysis_id
                    );
                  }}
                  key={analysis.analysis_id}
                >
                  <p className="text-sm font-semibold">
                    {analysis.analysis_json.title}
                  </p>
                  <p className="text-sm text-gray-400 overflow-ellipsis hidden md:block">
                    {clipStringToLength(
                      analysis.analysis_json.summary || "No summary",
                      100
                    )}
                  </p>
                </div>
              ))}
            </div>
          </div>
          <div className="w-3/4 p-4  max-h-full overflow-scroll inline-block align-top">
            <div className="mt-4 md:mt-0 pb-20">
              <div className="">
                {drawerSelectedAnalysisId ? (
                  <OracleAnalysis
                    key={drawerSelectedAnalysisId}
                    analysis={analyses[drawerSelectedAnalysisId]}
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center h-full">
                    <div className="mb-2 text-sm text-gray-400 dark:text-gray-500 text-center">
                      Select an analysis or <br /> type your question below to
                      start a new one
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="z-0 absolute bottom-0 left-1/4 w-3/4 h-20 transition-all group">
            <div
              className={twMerge(
                "absolute -bottom-20 w-full h-20 z-10 transition-all",
                drawerSelectedAnalysisId === null
                  ? "bottom-0"
                  : "group-hover:bottom-0"
              )}
            >
              <div className="bg-gray-50 left-0 right-0 mx-auto w-5/12 rounded-lg border border-gray-300 shadow-custom overflow-hidden p-2">
                <Input
                  // disabled={loading}
                  rootClassNames="mb-1"
                  inputClassNames="h-9 border-b-2 border-b-gray-300/50"
                  onPressEnter={(e) => {
                    if (!e.target.value) return;

                    const token = localStorage.getItem("defogToken");

                    try {
                      // setLoading(true);
                      // const analysisId = crypto.randomUUID();
                      // setLoadingAnalysisId(analysisId);
                      // generateNewAnalysis(
                      //   reportId,
                      //   analysisId,
                      //   recommendationIdx,
                      //   keyName,
                      //   token,
                      //   e.target.value,
                      //   analyses.map((d) => d.analysis_json)
                      // )
                      //   .then((d) => {
                      //     const newAnalysis: AnalysisParsed = {
                      //       analysis_id: analysisId,
                      //       mdx: d.mdx,
                      //       tables: d.tables || {},
                      //       multiTables: d.multiTables || {},
                      //       images: d.images || {},
                      //       analysis_json: d.analysis
                      //     };
                      //     setAnalyses([...analyses, newAnalysis]);
                      //     setLoading(false);
                      //     setLoadingAnalysisId(null);
                      //   })
                      //   .catch((e) => {
                      //     console.error(e);
                      //     setLoading(false);
                      //     setLoadingAnalysisId(null);
                      // });
                    } catch (error) {
                      console.error(error);
                      // setLoading(false);
                      // setLoadingAnalysisId(null);
                    }
                  }}
                  placeholder="Explore further"
                />
                <div className="text-xs text-gray-800/40 w-10/12">
                  <span>Type and Press Enter to start a new analysis</span>
                </div>
              </div>
            </div>
          </div>
        </Drawer> */}
      </div>
    </OracleReportContext.Provider>
  );
}
