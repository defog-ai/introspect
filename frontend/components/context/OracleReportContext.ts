// import type { Table } from "@defogdotai/agents-ui-components/core-ui";
import { createContext } from "react";

// import { Table } from "@defogdotai/agents-ui-components/core-ui";
export interface OracleReportContext {
  /** API Key name */
  keyName: string;
  /** Report ID */
  reportId: string;
  /**
   * Holds the images for an oracle report
   */
  images: {
    [key: string]: {
      /** Source path on the backend */
      src: string;
      /** Alt text */
      alt: string;
    };
  };

  /**
   * Holds the tables for an oracle report
   */
  tables: {
    [key: string]: {
      columns: [];
      data: [];
    };
  };
}

/**
 * Holds the context for the oracle reports
 */
export const OracleReportContext = createContext<OracleReportContext>({
  keyName: "",
  reportId: "",
  tables: {},
  images: {},
});
