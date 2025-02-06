"use client";
import { useEffect, useRef, useState } from "react";
import { SpinningLoader } from "@defogdotai/agents-ui-components/core-ui";
import {
  getReportMDX,
  getReportAnalysisIds,
  getReportExecutiveSummary,
  extensions,
  parseMDX,
  getReportComments,
  commentManager,
} from "$components/oracle/oracleUtils";

import { EditorProvider } from "@tiptap/react";
import React from "react";
import {
  OracleReportComment,
  OracleReportContext,
  Summary,
} from "$components/oracle/OracleReportContext";
import { OracleNav } from "$components/oracle/reports/OracleNav";
import { AgentConfigContext } from "@defogdotai/agents-ui-components/agent";

export default function ViewOracleReport() {
  const [keyName, setKeyName] = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setKeyName(params.get("keyName"));
    setReportId(params.get("reportId"));
  }, []);

  const reportStatus = useRef<string | null>(null);
  const [tables, setTables] = useState<any>({});
  const [multiTables, setMultiTables] = useState<any>({});
  const [images, setImages] = useState<any>({});
  const [analysisIds, setAnalysisIds] = useState<string[]>([]);
  const [comments, setComments] = useState<OracleReportComment[]>([]);

  const token = useRef<string>(null);

  const [mdx, setMDX] = useState<string | null>(null);
  const [executiveSummary, setExecutiveSummary] = useState<Summary | null>(
    null
  );

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const setup = async (reportId: string, keyName: string) => {
      try {
        token.current =
          localStorage.getItem("defogToken") ||
          "bdbe4d376e6c8a53a791a86470b924c0715854bd353483523e3ab016eb55bcd0";
        setLoading(true);
        const [mdx, status] = await getReportMDX(
          reportId,
          keyName,
          token.current
        );

        reportStatus.current = status;

        if (!mdx) {
          throw Error();
        }

        const parsed = parseMDX(mdx);

        setTables(parsed.tables);
        setImages(parsed.images);
        setMultiTables(parsed.multiTables);

        const sum: Summary = await getReportExecutiveSummary(
          reportId,
          keyName,
          token.current
        );

        // add ids to each recommendation
        sum.recommendations = sum.recommendations.map((rec) => ({
          id: crypto.randomUUID(),
          ...rec,
        }));

        const analysisIds = await getReportAnalysisIds(
          reportId,
          keyName,
          token.current
        );

        const fetchedComments = await getReportComments(
          reportId,
          keyName,
          token.current
        );

        setExecutiveSummary(sum);
        setAnalysisIds(analysisIds);

        setComments(fetchedComments);
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
    // sad reality for getting the chart container to work
    // it makes a request to this api endpoint to edit the chart's config
    // which defaults to demo.defog.ai if not provided
    // (╯°□°)╯︵ ┻━┻
    <AgentConfigContext.Provider
      // @ts-ignore
      value={{ val: { apiEndpoint: process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "" } }}
    >
      <OracleReportContext.Provider
        value={{
          tables: tables,
          multiTables: multiTables,
          images: images,
          analysisIds: analysisIds,
          executiveSummary: executiveSummary,
          reportId: reportId,
          keyName: keyName,
          token: token.current,
          commentManager: commentManager({
            reportId: reportId,
            keyName: keyName,
            token: token.current,
            initialComments: comments,
          }),
        }}
      >
        <div className="relative">
          <EditorProvider
            extensions={extensions}
            content={mdx}
            immediatelyRender={false}
            editable={false}
            slotBefore={<OracleNav />}
            editorProps={{
              attributes: {
                class:
                  "oracle-report-tiptap relative prose prose-base dark:prose-invert mx-auto p-2 mb-12 md:mb-0 focus:outline-none *:cursor-default",
              },
            }}
          >
          </EditorProvider>
        </div>
      </OracleReportContext.Provider>
    </AgentConfigContext.Provider>
  );
}
