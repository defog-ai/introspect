import { parseData } from "@defogdotai/agents-ui-components/agent";
import setupBaseUrl from "./setupBaseUrl";
import type {
  Analysis,
} from "$components/context/OracleReportContext";

export type { Analysis };

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

/**
 *
 * Parses all matches for an HTML-esque tag from the given string.
 * Returns the matching string, and the attributes that were found.
 */
function findTag(
  text: string,
  tag: string
): {
  fullText: string;
  attributes: { [key: string]: string };
  innerContent: string;
}[] {
  // full match of a tag
  const fullMatchRegex = new RegExp(
    `<${tag}(\\s+[^>]*?)?>(?:[^<]|<(?!</${tag}>))*?</${tag}>|<${tag}(\\s+[^>]*?)?/>`,
    "gi"
  );

  const attributesRegex = /([\w-]+)=[\{'"]([\s\S]+?)[\}'"][ \>]/gi;
  // everything *inside* the tag. This doesn't include attributes
  const innerContentRegex = />([\s\S]+?)</;
  const matches = [];
  let match: RegExpExecArray | null;

  while ((match = fullMatchRegex.exec(text)) !== null) {
    const fullText = match[0];
    // we want to find the opening tag separately, to avoid getting attributes of nested tags
    const tagOpenRegex = new RegExp(`<${tag}([\\s\\S]*?)/?>`, "gi");
    const tagOpenMatch = tagOpenRegex.exec(fullText);

    const attributes = {};
    if (tagOpenMatch) {
      let attributeMatch;
      while (
        (attributeMatch = attributesRegex.exec(tagOpenMatch[0])) !== null
      ) {
        attributes[attributeMatch[1]] = attributeMatch[2];
      }
    }

    const innerContentMatch = innerContentRegex.exec(fullText);
    const innerContent = innerContentMatch ? innerContentMatch[1] : "";
    matches.push({ fullText, attributes, innerContent: innerContent });
  }

  return matches;
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
  const parsed = {
    tables: {},
    multiTables: {},
  };
  const tables = findTag(mdx, "table");

  // replace tables with oracle-tables
  for (const table of tables) {
    const id = crypto.randomUUID();
    mdx = mdx.replace(
      table.fullText,
      `<oracle-table id="${id}"></oracle-table>`
    );
    const { columns, data } = parseData(table.attributes.csv);
    parsed.tables[id] = { columns, data, ...table };
  }

  // find multi tables
  const multiTables = findTag(mdx, "multitable");

  // replace multiTables with oracle-multi-tables
  for (const multiTable of multiTables) {
    const id = crypto.randomUUID();
    //   find table ids
    const tables = findTag(multiTable.fullText, "oracle-table");

    mdx = mdx.replace(
      multiTable.fullText,
      `<oracle-multi-table id="${id}"></oracle-multi-table>`
    );

    parsed.multiTables[id] = {
      tableIds: tables.map((t) => t.attributes.id),
      ...multiTable,
    };
  }

  return { mdx: mdx, ...parsed };
}

/**
 *
 * Parse images from an mdx string.
 *
 * Looks for `<Image src={SRC} alt={ALT_TEXT} />`
 */
export function parseImages(mdx: string) {
  // parse images
  const parsed = {
    images: {},
  };
  const images = findTag(mdx, "image");

  // replace images with oracle-images
  for (const image of images) {
    const id = crypto.randomUUID();
    mdx = mdx.replace(
      image.fullText,
      `<oracle-image id="${id}"></oracle-image>`
    );
    parsed.images[id] = image;
  }

  return { mdx: mdx, ...parsed };
}

export const TABLE_TYPE_TO_NAME = {
  table_csv: "Aggregated data",
  fetched_table_csv: "Fetched data",
  anomalies_csv: "Anomalies data",
};

class MDX {
  mdx: string;
  tables: { [key: string]: { columns: any[]; data: any[]; attributes?: { [key: string]: string }; fullText?: string } };
  multiTables: { [key: string]: { tableIds: string[]; attributes?: { [key: string]: string }; fullText?: string } };
  images: { [key: string]: { src: string; alt: string; attributes?: { [key: string]: string }; fullText?: string } };

  constructor(mdx: string) {
    this.mdx = mdx;
    this.tables = {};
    this.multiTables = {};
    this.images = {};
  }

  parseTables = () => {
    let parsed = parseTables(this.mdx);
    this.tables = parsed.tables;
    this.multiTables = parsed.multiTables;
    this.mdx = parsed.mdx;

    return this;
  };

  parseImages = () => {
    let parsed = parseImages(this.mdx);
    this.images = parsed.images;
    this.mdx = parsed.mdx;

    return this;
  };

  getParsed = () => {
    return Object.assign(
      {},
      {
        mdx: this.mdx,
        tables: Object.assign({}, this.tables),
        multiTables: Object.assign({}, this.multiTables),
        images: Object.assign({}, this.images),
      }
    );
  };
}

/**
 *
 * Parse an mdx string
 *
 */
export const parseMDX = (mdx: string): ReturnType<MDX["getParsed"]> => {
  let parsed = new MDX(mdx);

  parsed.parseTables().parseImages();

  const t = parsed.getParsed();

  return t;
};

export const generateNewAnalysis = async (
  reportId: string,
  analysisId: string,
  recommendationIdx: number,
  keyName: string,
  token: string,
  question: string,
  previousAnalyses: Analysis[]
) => {
  const res = await fetch(setupBaseUrl("http", `oracle/generate_analysis`), {
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
      analysis_id: analysisId,
      new_analysis_question: question,
      previous_analyses: previousAnalyses,
      recommendation_idx: recommendationIdx,
    }),
  });

  if (!res.ok) {
    throw new Error("Failed to generate new analysis");
  }

  const data = await res.json();

  if (data.error) {
    throw new Error(data.error);
  }

  return data;
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

  return data.analyses;
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

export const getAnalysisStatus = async (
  reportId: string,
  analysisId: string,
  keyName: string,
  token: string
) => {
  const res = await fetch(setupBaseUrl("http", `oracle/get_analysis_status`), {
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
      analysis_id: analysisId,
    }),
  });

  if (!res.ok) {
    throw new Error("Failed to fetch analysis status");
  }

  const data = await res.json();

  return data.status;
};
