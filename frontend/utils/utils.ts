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
