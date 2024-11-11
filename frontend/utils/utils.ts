import setupBaseUrl from "./setupBaseUrl";

export const addTool = async ({
  tool_name,
  function_name,
  description,
  code,
  input_metadata,
  output_metadata,
  no_code = false,
}) => {
  const addToolEndpoint = setupBaseUrl("http", "add_tool");
  const payload = {
    tool_name,
    function_name,
    description,
    code,
    input_metadata,
    output_metadata,
    no_code: no_code,
  };
  try {
    const res = await fetch(addToolEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error("Failed to add tool");
    }

    const json = await res.json();
    return json;
  } catch (e) {
    console.error(e);
    return { success: false, error_message: e };
  }
};

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
