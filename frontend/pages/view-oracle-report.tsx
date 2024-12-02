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
import { parseTables, parseImages } from "$utils/oracleUtils";

import StarterKit from "@tiptap/starter-kit";
import { Markdown } from "tiptap-markdown";
import { EditorProvider } from "@tiptap/react";
import React from "react";
import { OracleReportContext } from "$components/context/OracleReportContext";
import { OracleReportImageExtension } from "$components/oracle/reports/OracleReportImage";
import { LeftOutlined } from "@ant-design/icons";
import { OracleReportMultiTableExtension } from "$components/oracle/reports/OracleReportMultiTable";
import { OracleReportTableExtension } from "$components/oracle/reports/OracleReportTable";

const extensions = [
  StarterKit,
  OracleReportMultiTableExtension,
  OracleReportTableExtension,
  OracleReportImageExtension,
  Markdown,
];

export default function ViewOracleReport() {
  const router = useRouter();

  const [tables, setTables] = useState<any>({});
  const [multiTables, setMultiTables] = useState<any>({});
  const [images, setImages] = useState<any>({});

  const feedbackTextArea = useRef<HTMLTextAreaElement>(null);

  const [mdx, setMDX] = useState<string | null>(null);

  const [currentFeedback, setCurrentFeedback] = useState<string | null>(
    undefined
  );

  const [error, setError] = useState<string | null>(null);

  const [feedbackModalOpen, setFeedbackModalOpen] = useState<boolean>(false);

  const message = useContext(MessageManagerContext);

  useEffect(() => {
    const getMDX = async (reportId: string, keyName: string) => {
      try {
        const token = localStorage.getItem("defogToken");
        const res = await fetch(setupBaseUrl("http", `oracle/get_report_mdx`), {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/pdf",
            // disable cors for the download
            mode: "no-cors",
          },
          body: JSON.stringify({
            key_name: keyName,
            token: token,
            report_id: reportId,
          }),
        });

        const data = await res.json();

        let mdx = data.mdx;

        if (!mdx) {
          throw Error();
        }

        if (!data.mdx) {
          throw Error();
        }

        let parsed = {
          ...parseTables(mdx),
        };

        console.log(parsed);

        parsed = {
          ...parsed,
          ...parseImages(parsed.mdx),
        };

        setTables(parsed.tables);
        // @ts-ignore
        setImages(parsed.images);
        setMultiTables(parsed.multiTables);
        setCurrentFeedback(data.feedback || undefined);

        setMDX(parsed.mdx);
      } catch (e) {
        console.error(e);
        setError("Could not fetch MDX for report: " + reportId);
      }
    };

    const reportId = Array.isArray(router?.query?.reportId)
      ? router?.query?.reportId[0]
      : router?.query?.reportId;

    const keyName = Array.isArray(router?.query?.keyName)
      ? router?.query?.keyName[0]
      : router?.query?.keyName;

    if (reportId && keyName) {
      getMDX(reportId, keyName);
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
          "w-full h-full min-h-60 flex flex-col justify-center items-center bg-rose-100 text-red text-center rounded-md p-2"
        }
      >
        <div className="mb-2 text-sm text-rose-500">{error}</div>
      </div>
    );
  }

  if (!mdx) {
    return (
      <div
        className={
          "w-full h-full min-h-60 flex flex-col justify-center items-center "
        }
      >
        <div className="mb-2 text-sm text-gray-400">Fetching</div>
        <SpinningLoader classNames="w-5 h-5 text-gray-500" />
      </div>
    );
  }

  return (
    <OracleReportContext.Provider
      value={{
        tables: tables,
        multiTables: multiTables,
        images: images,
        reportId: Array.isArray(router.query.reportId)
          ? router.query.reportId[0]
          : router.query.reportId,
        keyName: Array.isArray(router.query.keyName)
          ? router.query.keyName[0]
          : router.query.keyName,
      }}
    >
      <div className="relative">
        <div className="flex flex-row fixed min-h-12 bottom-0 w-full bg-gray-50 md:bg-transparent md:w-auto md:sticky md:top-0 p-2 z-10 md:h-0">
          {/* @ts-ignore */}
          <Button
            onClick={() => router.push("/oracle-frontend")}
            className="bg-transparent border-none hover:bg-transparent"
          >
            <LeftOutlined className="w-2" /> All reports
          </Button>

          {/* @ts-ignore */}
          <Button
            onClick={() => setFeedbackModalOpen(true)}
            className="ml-auto"
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
                "oracle-report-tiptap prose prose-base mx-auto p-2 mb-12 md:mb-0 focus:outline-none",
            },
          }}
        />
      </div>
    </OracleReportContext.Provider>
  );
}
