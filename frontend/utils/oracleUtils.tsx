import { parseData } from "@defogdotai/agents-ui-components/agent";
import setupBaseUrl from "./setupBaseUrl";
import type {
  Analysis,
  Summary,
} from "$components/context/OracleReportContext";

import { OracleReportMultiTableExtension } from "$components/oracle/reports/OracleReportMultiTable";
import { OracleReportTableExtension } from "$components/oracle/reports/OracleReportTable";
import { RecommendationTitle } from "$components/oracle/reports/OracleReportRecommendationTitle";
import StarterKit from "@tiptap/starter-kit";
import { OracleReportImageExtension } from "$components/oracle/reports/OracleReportImage";
import { Markdown } from "tiptap-markdown";

export const extensions = [
  StarterKit,
  RecommendationTitle,
  OracleReportMultiTableExtension,
  OracleReportTableExtension,
  OracleReportImageExtension,
  Markdown,
];

interface TableAttributes {
  /**
   * The type of the table.
   */
  type: string;
  /**
   * The csv data of the table.
   */
  csv: string;
  /**
   * The id of the table.
   */
  id: string;
  [key: string]: string;
}

/**
 *
 * Parse tables from an mdx string.
 * For example:
 * ```jsx
 * <MultiTable>
 *  <Table id={TABLE_ID} />
 *  <Table id={xxx} />
 * </MultiTable>
 * ```
 * Or just:
 * ```jsx
 * <Table id={TABLE_ID} custom-attr={TT} />
 * ```
 *
 * 1. First look for table tags. Parse all data in them.
 * 2. Replace those table tags with oracle-table tags. Keep storing the parsed data with the table id inside a dict.
 * 3. Then look for multi-table tags. For each multi-table tag, replace it with an oracle-multi-table tag.
 * 4. Store the table ids within each multi table tag inside a dict.
 * 5. Replace all content inside a multi table tag with nothing.
 *
 */
export function parseTables(mdx: string) {
  const tables = {};
  const multiTables = {};
  const multiTableRegex = /<MultiTable>([\s\S]*?)<\/MultiTable>/g;
  const tableRegex = /<Table\s+([^>]*?)\s*\/>/g;
  const attributesRegex = /([\w-]+)=[\{'\"]([\s\S]+?)[\}'\"]/g;
  let newMdx = mdx;

  // first find all tables
  let tableMatch: RegExpExecArray | null;
  while ((tableMatch = tableRegex.exec(mdx)) !== null) {
    // find all attributes
    const tableId = crypto.randomUUID();
    const attributes: TableAttributes = {
      csv: null,
      type: null,
      id: tableId,
    };
    let attributeMatch;

    while ((attributeMatch = attributesRegex.exec(tableMatch[1])) !== null) {
      attributes[attributeMatch[1]] = attributeMatch[2];
    }

    const { columns, data } = parseData(attributes.csv);
    tables[tableId] = { columns, data, ...attributes };

    // replace the table with an oracle-table tag
    newMdx = newMdx.replace(
      tableMatch[0],
      `<oracle-table id="${tableId}"></oracle-table>`
    );
  }

  // handle MultiTables
  mdx = newMdx;

  let multiMatch: RegExpExecArray | null;
  while ((multiMatch = multiTableRegex.exec(mdx)) !== null) {
    const multiTableContent = multiMatch[1];
    const multiTableId = crypto.randomUUID();
    const tableIds = [];

    // Find all tables within this MultiTable
    let localTableIdMatch: RegExpExecArray | null;
    const localTableIdRegex = /id=["'](.*?)["']/g;
    while (
      (localTableIdMatch = localTableIdRegex.exec(multiTableContent)) !== null
    ) {
      const tableId = localTableIdMatch[1];
      tableIds.push(tableId);
    }

    // Store MultiTable metadata
    multiTables[multiTableId] = { tableIds };

    // Replace the entire MultiTable with a single oracle-multi-table tag
    newMdx = newMdx.replace(
      multiMatch[0],
      `<oracle-multi-table id="${multiTableId}"></oracle-multi-table>`
    );
  }

  return { mdx: newMdx, tables, multiTables };
}

/**
 *
 * Parse images from an mdx string.
 *
 * Looks for `<Image src={SRC} alt={ALT_TEXT} />`
 */
export function parseImages(mdx: string) {
  const images = {};
  const imageRegex =
    /<Image src=[\{'\"]([\s\S]+?)[\}'\"] alt=[\{'\"]([\s\S]+?)[\}'\"] \/>/g;

  let newMdx = mdx;

  let match: RegExpExecArray | null;
  while ((match = imageRegex.exec(mdx)) !== null) {
    const src = match[1];
    const alt = match[2];

    const id = crypto.randomUUID();

    newMdx = newMdx.replace(
      match[0],
      `<oracle-image id="${id}"></oracle-image>`
    );

    images[id] = { src, alt };
  }

  return { mdx: newMdx, images };
}

export const TABLE_TYPE_TO_NAME = {
  table_csv: "Aggregated data",
  fetched_table_csv: "Fetched data",
  anomalies_csv: "Anomalies data",
};

/**
 *
 * Parse tables, multitables and images from an mdx string
 *
 */
export const parseTablesAndImagesInMdx = (mdx: string) => {
  let parsed = {
    ...parseTables(mdx),
  };

  parsed = {
    ...parsed,
    ...parseImages(parsed.mdx),
  };

  return parsed;
};

/**
 * Converts the summary dictionary to markdown for compatibility with the
 * report markdown display.
 *
 * @param summary The summary object containing title, introduction and recommendations
 * @returns A markdown string with the formatted content
 */
export const createMdxFromExecutiveSummary = (summary: Summary): string => {
  if (!summary) {
    console.error("Invalid summary object provided");
    return "";
  }

  let md = `# ${summary.title}\n\n${summary.introduction}\n\n`;

  summary.recommendations.forEach((recommendation) => {
    md += `<oracle-recommendation id="${recommendation.id}></oracle-recommendation>\n\n`;
  });

  return md;
};

export const getReportAnalyses = async (
  reportId: string,
  keyName: string,
  token: string
) => {
  const res = await fetch(
    setupBaseUrl("http", `oracle/get_report_analysis_list`),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        mode: "no-cors",
      },
      body: JSON.stringify({
        key_name: keyName,
        token: token,
        report_id: reportId,
      }),
    }
  );

  if (!res.ok) {
    throw new Error("Failed to fetch analyses");
  }

  const data = await res.json();

  if (!data.analyses) {
    throw new Error("No analyses found");
  }

  // Convert the array of analyses into an object with analysis_id as keys
  const analysesMap = data.analyses.reduce((acc: any, analysis: any) => {
    acc[analysis.analysis_id] = analysis;
    return acc;
  }, {});

  return analysesMap;
};

export const getReportMDX = async (
  reportId: string,
  keyName: string,
  token: string
) => {
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

  if (!res.ok) {
    throw new Error("Failed to fetch mdx");
  }

  const data = await res.json();

  return data.mdx;
};

export const getReportExecutiveSummary = async (
  reportId: string,
  keyName: string,
  token: string
) => {
  const res = await fetch(setupBaseUrl("http", `oracle/get_report_summary`), {
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

  if (!res.ok) {
    throw new Error("Failed to fetch executive summary");
  }

  const data = await res.json();

  return data.executive_summary;
};

export const getReportFeedback = async (
  reportId: string,
  keyName: string,
  token: string
) => {
  const res = await fetch(setupBaseUrl("http", `oracle/get_report_feedback`), {
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

  if (!res.ok) {
    throw new Error("Failed to fetch feedback");
  }

  const data = await res.json();

  return data.feedback;
};

export const getReportImage = async (
  reportId: string,
  keyName: string,
  token: string,
  imageFileName: string
) => {
  const res = await fetch(setupBaseUrl("http", `oracle/get_report_image`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/pdf",
      // disable cors for the download
      mode: "no-cors",
    },
    body: JSON.stringify({
      image_file_name: imageFileName,
      key_name: keyName,
      report_id: reportId,
      token: token,
    }),
  });

  if (!res.ok) {
    throw new Error("Failed to fetch image");
  }

  const data = await res.json();

  if (!data.encoded) {
    throw new Error("Error fetching image");
  }

  return data.encoded;
};

export const getReportAnalysesMdx = async (
  reportId: string,
  keyName: string,
  token: string
) => {
  const res = await fetch(
    setupBaseUrl("http", `oracle/get_report_analyses_mdx`),
    {
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
    }
  );

  if (!res.ok) {
    throw new Error("Failed to fetch analyses mdx");
  }

  const data = await res.json();

  return data.analyses_mdx;
};
