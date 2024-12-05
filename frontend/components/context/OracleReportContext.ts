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
  round?: number;
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
    [key: string]: Analysis;
  };

  /**
   * Holds the mdx for all the analyses for a report
   */
  analysesMdx: {
    [key: string]: string;
  };

  /**
   * Holds the executive summary for an oracle report
   */
  executiveSummary: Summary;

  /**
   * Holds the images for an oracle report
   */
  images: {
    [key: string]: {
      /** Source path on the backend */
      src: string;
      /** Alt text */
      alt: string;
      attributes?: Object;
      fullText?: string;
    };
  };

  /**
   * Holds the multi tables for an oracle report
   */
  multiTables: {
    [key: string]: {
      tableIds: string[];
      attributes?: Object;
      fullText?: string;
    };
  };

  /**
   * Holds the tables for an oracle report
   */
  tables: {
    [key: string]: {
      columns: [];
      data: [];
      id?: string;
      type?: string;
      csv?: string;
      attributes?: Object;
      fullText?: string;
    };
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
  analysesMdx: {},
});
