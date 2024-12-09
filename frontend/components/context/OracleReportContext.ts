import { Summary } from "$utils/oracleUtils";
import { createContext } from "react";

export interface IndependentVariableGroup {
  name: string;
  description: string;
  "table.column": string[];
}

export interface Artifacts {
  fetched_table_csv?: {
    artifact_content?: string;
    data?: any[];
    columns?: any[];
  };
}

interface Recommendation {
  title: string;
  insight: string;
  action: string;
  id: string;
}

export interface Summary {
  title: string;
  introduction: string;
  recommendations: Recommendation[];
}

export interface Working {
  generated_sql: string;
}

export interface Analysis {
  analysis_id: number;
  generated_qn: string;
  independent_variable_group: IndependentVariableGroup;
  artifacts: Artifacts;
  working: Working;
  summary?: string;
  title?: string;
  round?: number;
}

interface MultiTable {
  [key: string]: {
    tableIds: string[];
    attributes?: { [key: string]: string };
    fullText?: string;
  };
}

interface Table {
  columns: [];
  data: [];
  id?: string;
  type?: string;
  csv?: string;
  attributes?: { [key: string]: string };
  fullText?: string;
}

interface Image {
  /** Source path on the backend */
  src: string;
  /** Alt text */
  alt: string;
  attributes?: Object;
  fullText?: string;
}

export interface AnalysisParsed {
  mdx: string;
  tables: {
    [key: string]: Table;
  };
  multiTables: {
    [key: string]: MultiTable;
  };
  images: {
    [key: string]: Image;
  };
  json: Analysis;
}

export interface OracleReportContext {
  /** API Key name */
  keyName: string;
  /** Report ID */
  reportId: string;
  /**
   * Holds all the analysis data for an oracle report
   */
  analyses: {
    [key: string]: AnalysisParsed;
  };

  /**
   * Holds the executive summary for an oracle report
   */
  executiveSummary: Summary;

  /**
   * Holds the images for an oracle report
   */
  images: {
    [key: string]: Image;
  };

  /**
   * Holds the multi tables for an oracle report
   */
  multiTables: {
    [key: string]: MultiTable;
  };
  /**
   * Holds the tables for an oracle report
   */
  tables: {
    [key: string]: Table;
  };
}

/**
 * Holds the context for the oracle reports
 */
export const OracleReportContext = createContext<OracleReportContext>({
  keyName: "",
  reportId: "",
  multiTables: {},
  tables: {},
  images: {},
  analyses: {},
  executiveSummary: "",
});
