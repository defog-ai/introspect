import setupBaseUrl from "$utils/setupBaseUrl";
import { useRouter } from "next/router";
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
  getReportAnalyses,
  getReportExecutiveSummary,
  extensions,
  parseMDX,
} from "$utils/oracleUtils";

import { EditorProvider } from "@tiptap/react";
import React from "react";
import {
  Analysis,
  AnalysisParsed,
  OracleReportContext,
  Summary,
} from "$components/context/OracleReportContext";
import { LeftOutlined } from "@ant-design/icons";

export default function ViewOracleReport() {
  const router = useRouter();

  const [tables, setTables] = useState<any>({});
  const [multiTables, setMultiTables] = useState<any>({});
  const [images, setImages] = useState<any>({});
  const [analyses, setAnalyses] = useState<{
    [key: string]: AnalysisParsed;
  }>({});

  const feedbackTextArea = useRef<HTMLTextAreaElement>(null);

  const [mdx, setMDX] = useState<string | null>(null);
  const [executiveSummary, setExecutiveSummary] = useState<Summary | null>(
    null
  );

  const [currentFeedback, setCurrentFeedback] = useState<string | null>(
    undefined
  );

  const [error, setError] = useState<string | null>(null);

  const [feedbackModalOpen, setFeedbackModalOpen] = useState<boolean>(false);

  const message = useContext(MessageManagerContext);

  useEffect(() => {
    const setup = async (reportId: string, keyName: string) => {
      try {
        const token = localStorage.getItem("defogToken");
        let mdx = await getReportMDX(reportId, keyName, token);

        if (!mdx) {
          throw Error();
        }

        const parsed = parseMDX(mdx);

        setTables(parsed.tables);
        setImages(parsed.images);
        setMultiTables(parsed.multiTables);
        const feedback = await getReportFeedback(reportId, keyName, token);
        setCurrentFeedback(feedback || undefined);

        const analysesJsons = await getReportAnalyses(reportId, keyName, token);

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

        const analyses = {};

        analysesJsons.map((analysis) => {
          analyses[analysis.analysis_id] = {
            analysis_id: analysis.analysis_id,
            ...analysis,
            ...parseMDX(analysis.mdx),
          };
        });

        console.log(analyses);

        setAnalyses(analyses);

        setMDX(parsed.mdx);
      } catch (e) {
        console.error(e);
        setError(e.message);
      }
    };

    const reportId = Array.isArray(router?.query?.reportId)
      ? router?.query?.reportId[0]
      : router?.query?.reportId;

    const keyName = Array.isArray(router?.query?.keyName)
      ? router?.query?.keyName[0]
      : router?.query?.keyName;

    if (reportId && keyName) {
      setup(reportId, keyName);
    }
  }, [router.query]);

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
        report_id: router.query.reportId,
        key_name: router.query.keyName,
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
  }, [router.query.reportId, router.query.keyName, message]);

  if (error) {
    return (
      <div
        className={
          "w-full h-full min-h-60 flex flex-col justify-center items-center bg-rose-100 dark:bg-rose-900 text-red text-center rounded-md p-2"
        }
      >
        <div className="mb-2 text-sm text-rose-500 dark:text-rose-400">{error}</div>
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
        <div className="mb-2 text-sm text-gray-400 dark:text-gray-500">Fetching</div>
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
        analyses: analyses,
        executiveSummary: executiveSummary,
        reportId: Array.isArray(router.query.reportId)
          ? router.query.reportId[0]
          : router.query.reportId,
        keyName: Array.isArray(router.query.keyName)
          ? router.query.keyName[0]
          : router.query.keyName,
      }}
    >
      <div className="relative">
        <div className="flex flex-row fixed min-h-12 bottom-0 w-full bg-gray-50 dark:bg-gray-800 md:bg-transparent dark:md:bg-transparent md:w-auto md:sticky md:top-0 p-2 z-10 md:h-0">
          {/* @ts-ignore */}
          <Button
            onClick={() => router.push("/oracle-frontend")}
            className="bg-transparent border-none hover:bg-transparent text-gray-700 dark:text-gray-300"
          >
            <LeftOutlined className="w-2" /> All reports
          </Button>

          {/* @ts-ignore */}
          <Button
            onClick={() => setFeedbackModalOpen(true)}
            className="ml-auto text-gray-700 dark:text-gray-300"
          >
            Give feedback
          </Button>

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
          content={mdx}
          editable={false}
          editorProps={{
            attributes: {
              class:
                "oracle-report-tiptap prose prose-base dark:prose-invert mx-auto p-2 mb-12 md:mb-0 focus:outline-none",
            },
          }}
        />
      </div>
    </OracleReportContext.Provider>
  );
}
