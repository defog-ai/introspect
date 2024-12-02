import { createContext } from "react";

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
   * Holds the multi tables for an oracle report
   */
  multiTables: {
    [key: string]: {
      tableIds: string[];
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
});
