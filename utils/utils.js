import { contrast, random } from "chroma-js";
import setupBaseUrl from "../utils/setupBaseUrl";

export const getApiToken = async (
  username,
  hashed_pw,
  router,
  errorRoute = "/log-in"
) => {
  const url = "https://api.defog.ai/get_token";
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-hashed-password": hashed_pw,
      },
      body: JSON.stringify({
        username: username,
      }),
    });
  } catch (e) {
    router.push(errorRoute);
    return { success: false, error_message: e };
  }
  const json = await response.json();
  return json;
};

export const getAnalysis = async (reportId) => {
  const urlToConnect = setupBaseUrl("http", "get_report");
  let response;
  try {
    response = await fetch(urlToConnect, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        report_id: reportId,
      }),
    });
  } catch (e) {
    return { success: false, error_message: e };
  }
  const json = await response.json();
  return json;
};

export const getReport = getAnalysis;

export const createAnalysis = async (
  apiToken,
  username,
  customId = null,
  bodyData = {}
) => {
  const urlToConnect = setupBaseUrl("http", "create_analysis");
  let response;
  try {
    response = await fetch(urlToConnect, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        api_key: apiToken,
        custom_id: customId,
        username: username,
        ...bodyData,
      }),
    });
  } catch (e) {
    return { success: false, error_message: e };
  }
  const json = await response.json();
  return json;
};

export const createReport = createAnalysis;

export const getAllDocs = async (apiToken, username) => {
  const urlToConnect = setupBaseUrl("http", "get_docs");
  let response;
  try {
    response = await fetch(urlToConnect, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        api_key: apiToken,
        username: username,
      }),
    });
    return response.json();
  } catch (e) {
    return { success: false, error_message: e };
  }
};

export const getTableData = async (tableId) => {
  const urlToConnect = setupBaseUrl("http", "get_table_chart");
  let response;
  try {
    response = await fetch(urlToConnect, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        table_id: tableId,
      }),
    });
    return response.json();
  } catch (e) {
    return { success: false, error_message: e };
  }
};

export const getAllAnalyses = async (apiToken) => {
  const urlToConnect = setupBaseUrl("http", "get_analyses");
  let response;
  try {
    response = await fetch(urlToConnect, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        api_key: apiToken,
      }),
    });
    return response.json();
  } catch (e) {
    return { success: false, error_message: e };
  }
};

export const getToolboxes = async (username) => {
  const urlToConnect = setupBaseUrl("http", "get_toolboxes");
  let response;
  try {
    response = await fetch(urlToConnect, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: username,
      }),
    });
    return response.json();
  } catch (e) {
    return { success: false, error_message: e };
  }
};

// something that looks good against black text
export const getCursorColor = function () {
  // start with a random color
  const black = "#000";
  let color = random().hex();
  let cont = contrast(color, black);
  while (cont < 9) {
    // keep regenerating until we get a good contrast
    color = random().hex();
    cont = contrast(color, black);
  }

  return color;
};

export const aiBlocks = ["analysis", "table-chart"];

export const roundNumber = function (number) {
  if (number === null || number === undefined) {
    return null;
  }
  if (number < 1 && number > -1) {
    // exponential
    return number.toExponential(2);
  }
  if (number > 100000 || number < -100000) {
    // exponential
    return number.toExponential(2);
  }
  // rounded to 2 decimals
  return Math.round(number * 100) / 100;
};

export const getToolRunData = async (toolRunId) => {
  const url = setupBaseUrl("http", "get_tool_run");
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        tool_run_id: toolRunId,
      }),
    });
    return response.json();
  } catch (e) {
    return { success: false, error_message: e };
  }
};

export const isNullOrUndefined = function (val) {
  return val === null || val === undefined;
};

export const deleteDoc = async (docId) => {
  const url = setupBaseUrl("http", "delete_doc");
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        doc_id: docId,
      }),
    });
    return response.json();
  } catch (e) {
    return { success: false, error_message: e };
  }
};

export const getUserMetadata = async () => {
  const url = setupBaseUrl("http", "get_user_metadata");
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });
    return response.json();
  } catch (e) {
    return { success: false, error_message: e };
  }
};

export const toolDisplayNames = {
  data_fetcher_and_aggregator: "Fetch data from db",
  global_dict_data_fetcher_and_aggregator: "Query data",
  dataset_metadata_describer: "Dataset Metadata Describer",
  line_plot: "Line Plot",
  kaplan_meier_curve: "Kaplan Meier Curve",
  hazard_ratio: "Hazard Ratio",
  t_test: "T Test",
  anova_test: "ANOVA Test",
  wilcoxon_test: "Wilcoxon Test",
  boxplot: "Boxplot",
  heatmap: "Heatmap",
};

export const easyColumnTypes = {
  DBColumn: "Column name",
  "list[DBColumn]": "List of column names",
  "pandas.core.frame.DataFrame": "Dataframe",
  str: "String",
  int: "Integer",
  float: "Float",
  bool: "Boolean",
  "list[str]": "List of strings",
  list: "List",
};

// export const estimatorDefaultOptions = {
//   // function name
//   "line_plot": {
//     // function parameter name
//     "estimator": ["mean", "sum", "median", "std", "var", "count"]
//   },
//   "t_test": {
//     "t_test_type": ["paired", "unpaired"]
//   }
// }
