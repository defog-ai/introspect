import setupBaseUrl from "./setupBaseUrl";

/**
 *
 * Converts an array of object to a single object.
 *
 * @param {Array} arr - Array of objects to convert to objects
 * @param {string} key - The key of each object in `arr` to use as the key for the new object being created
 * @param {Array | null} includeKeys - If passed, only the given keys are included
 *
 * @example
 * const arr = [
 *   {"firstname": "John", "surname": "Carmack", "job": "programmer"},
 *   {"firstname": "Amitabh", "surname": "Bachchan", "job": "actor"},
 *   {"firstname": "Lewis", "surname": "Hamilton", "job": "racer"},
 * ]
 *
 * const firstName = arrayOfObjectsToObject(arr, "firstname")
 *
 * console.log(firstName)
 * // {
 * //    "John": {"firstname": "John", "surname": "Carmack", "job": "programmer"},
 * //    "Amitabh": {"firstname": "Amitabh", "surname": "Bachchan", "job": "actor"},
 * //    "Lewis": {"firstname": "Lewis", "surname": "Hamilton", "job": "racer"},
 * // }
 *
 * @returns
 */
export function arrayOfObjectsToObject(
  arr: Array<any>,
  key: string,
  includeKeys: Array<any> | null = null
) {
  return arr.reduce((acc, obj) => {
    acc[obj[key]] = Object.keys(obj).reduce((acc2, k) => {
      if (Array.isArray(includeKeys) && !includeKeys.includes(k)) {
        return acc2;
      }

      acc2[k] = obj[k];
      return acc2;
    }, {});

    return acc;
  }, {});
}

/**
 * Converts a string to lower case. Returns the passed parameter as is if it can't convert.
 * @param {string} str - The string to convert to lower case
 */
export function toLowerCase(str: string) {
  try {
    return str.toLowerCase();
  } catch (e) {
    return str;
  }
}

export const toSentenceCase = (str: string) => {
  if (!str) return "";
  return str[0].toUpperCase() + str.slice(1);
};

/**
 * Clips a string to a certain length and optionally adds an ellipsis if the string is longer than the length
 */
export const clipStringToLength = (
  str: string,
  length: number,
  addEllipsis = true
) => {
  if (str.length > length) {
    return str.slice(0, length) + (addEllipsis ? "..." : "");
  }
  return str;
};

export const fetchMetadata = async (token: string, dbName: string) => {
  const res = await fetch(setupBaseUrl("http", `integration/get_metadata`), {
    method: "POST",
    body: JSON.stringify({ token, db_name: dbName }),
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    throw new Error("Failed to get metadata");
  }
  return await res.json();
};

export type DbType =
  | "postgres"
  | "redshift"
  | "snowflake"
  | "databricks"
  | "bigquery"
  | "sqlserver";

export interface DbCreds {
  postgres: {
    host: string;
    port: string;
    user: string;
    password: string;
    database: string;
  };
  redshift: {
    host: string;
    port: string;
    user: string;
    password: string;
    database: string;
    schema: string;
  };
  snowflake: {
    account: string;
    warehouse: string;
    user: string;
    password: string;
  };
  databricks: {
    server_hostname: string;
    access_token: string;
    http_path: string;
    schema: string;
  };
  bigquery: {
    credentials_file_content: string;
  };
  sqlserver: {
    server: string;
    database: string;
    user: string;
    password: string;
  };
}

export type DbMetadata = Array<{
  table_name: string;
  column_name: string;
  data_type: string;
  column_description: string;
}>;

export interface DbInfo {
  db_name?: string;
  db_type?: DbType;
  db_creds?: DbCreds[DbType];
  can_connect?: boolean;
  metadata?: DbMetadata;
  selected_tables?: string[];
  tables?: string[];
}

export const getDbInfo = async (
  token: string,
  dbName: string
): Promise<DbInfo> => {
  const res = await fetch(setupBaseUrl("http", `integration/get_db_info`), {
    method: "POST",
    body: JSON.stringify({ token, db_name: dbName }),
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    throw new Error("Failed to get tables and db creds");
  } else {
    return await res.json();
  }
};

export const deleteDbInfo = async (token: string, dbName: string) => {
  const res = await fetch(setupBaseUrl("http", `integration/delete_db_info`), {
    method: "POST",
    body: JSON.stringify({ token, db_name: dbName }),
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    throw new Error("Failed to delete db info");
  } else {
    return await res.json();
  }
};

export const FILE_TYPES = {
  EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  OLD_EXCEL: "application/vnd.ms-excel",
  CSV: "text/csv",
};

/**
 * Simple function to check if given gile type exists in the FILE_TYPES object
 */
export function isValidFileType(fileType: string) {
  return Object.values(FILE_TYPES).find((f) => f === fileType);
}

interface UserFile {
  rows: { [key: string]: any }[];
  columns: { title: string }[];
}

export const uploadFile = async (
  token: string,
  fileName: string,
  fileBase64: string
): Promise<{ dbName: string; dbInfo: DbInfo }> => {
  const res = await fetch(setupBaseUrl("http", `upload_file_as_db`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      token: token,
      file_name: fileName,
      base_64_file: fileBase64,
    }),
  });

  if (!res.ok) {
    throw new Error(
      "Failed to create new api key name - are you sure your network is working?"
    );
  }
  const data = await res.json();
  return { dbName: data.db_name, dbInfo: data.db_info };
};

export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  var binary = "";
  var bytes = new Uint8Array(buffer);
  var len = bytes.byteLength;
  for (var i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}
