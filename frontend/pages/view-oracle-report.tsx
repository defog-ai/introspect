import setupBaseUrl from "$utils/setupBaseUrl";
import { useRouter } from "next/router";
import { createContext, useContext, useEffect, useState } from "react";
import { SpinningLoader } from "@defogdotai/agents-ui-components/core-ui";
import { parseTables, parseImages } from "$utils/oracleUtils";

import StarterKit from "@tiptap/starter-kit";
import { Markdown } from "tiptap-markdown";
import { EditorProvider } from "@tiptap/react";
import React from "react";
import { OracleReportContext } from "$components/context/OracleReportContext";
import { OracleReportTableExtension } from "$components/oracle/reports/OracleReportTable";
import { OracleReportImageExtension } from "$components/oracle/reports/OracleReportImage";

const extensions = [
  StarterKit,
  OracleReportTableExtension,
  OracleReportImageExtension,
  Markdown,
];

export default function ViewOracleReport() {
  const router = useRouter();

  const [tables, setTables] = useState<any>({});
  const [images, setImages] = useState<any>({});

  const [mdx, setMDX] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

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

        const tables = parseTables(mdx);
        mdx = tables.newMdx;

        const images = parseImages(mdx);
        mdx = images.newMdx;

        setImages(images.images);
        setTables(tables.tables);

        setMDX(mdx);
      } catch (e) {
        console.error(e);
        setError("Could not getch MDX for report: " + reportId);
      }
    };

    const reportId = router?.query?.reportId;
    const keyName = router?.query?.keyName;
    if (reportId && keyName) {
      getMDX(reportId, keyName);
    }
  }, [router.query]);

  if (error) {
    return (
      <div
        className={
          "w-full h-full min-h-60 flex flex-col justify-center items-center "
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
        images: images,
        reportId: router.query.reportId,
        keyName: router.query.keyName,
      }}
    >
      <EditorProvider
        extensions={extensions}
        content={mdx}
        editable={false}
        editorProps={{
          attributes: {
            class:
              "prose mx-auto p-2 focus:outline-none prose-code:text-gray-200 prose-code:text-shadow-none",
          },
        }}
      />
    </OracleReportContext.Provider>
  );
}
