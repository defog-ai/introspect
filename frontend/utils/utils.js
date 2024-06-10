import { contrast, random } from "chroma-js";
import setupBaseUrl from "$utils/setupBaseUrl";
import { Annotation, EditorState, Transaction } from "@codemirror/state";
import { Doc, XmlElement, applyUpdate, encodeStateAsUpdate } from "yjs";
import { v4 } from "uuid";
import { toolsMetadata } from "./tools_metadata";
import { csvParse } from "d3";
import { reFormatData } from "$components/defog-components/components/common/utils";

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

export const createAnalysis = async (token, customId = null, bodyData = {}) => {
  const urlToConnect = setupBaseUrl("http", "create_analysis");
  let response;
  try {
    response = await fetch(urlToConnect, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        custom_id: customId,
        token: token,
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

export const getAllDocs = async (token) => {
  const urlToConnect = setupBaseUrl("http", "get_docs");
  let response;
  try {
    response = await fetch(urlToConnect, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token: token,
      }),
    });
    return response.json();
  } catch (e) {
    return { success: false, error_message: e };
  }
};

export const getAllDashboards = getAllDocs;

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

export const getAllAnalyses = async () => {
  const urlToConnect = setupBaseUrl("http", "get_analyses");
  let response;
  try {
    response = await fetch(urlToConnect, {
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

export const getToolboxes = async (token) => {
  const urlToConnect = setupBaseUrl("http", "get_toolboxes");
  let response;
  try {
    response = await fetch(urlToConnect, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token: token,
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

export const toolDisplayNames = {
  data_fetcher_and_aggregator: "Fetch data from db",
  global_dict_data_fetcher_and_aggregator: "Query data",
  line_plot: "Line Plot",
  kaplan_meier_curve: "Kaplan Meier Curve",
  hazard_ratio: "Hazard Ratio",
  t_test: "T Test",
  anova_test: "ANOVA Test",
  wilcoxon_test: "Wilcoxon Test",
  boxplot: "Boxplot",
  heatmap: "Heatmap",
  fold_change: "Fold Change",
};

export const toolShortNames = {
  data_fetcher_and_aggregator: "Fetch ",
  global_dict_data_fetcher_and_aggregator: "Query ",
  line_plot: "Line",
  kaplan_meier_curve: "KM Curve",
  hazard_ratio: "Hazard Ratio",
  t_test: "T Test",
  anova_test: "ANOVA Test",
  wilcoxon_test: "Wilcoxon Test",
  boxplot: "Boxplot",
  heatmap: "Heatmap",
  fold_change: "Fold Change",
};

export const easyToolInputTypes = {
  DBColumn: "Column name",
  DBColumnList: "List of column names",
  "pandas.core.frame.DataFrame": "Dataframe",
  str: "String",
  int: "Integer",
  float: "Float",
  bool: "Boolean",
  "list[str]": "List of strings",
  list: "List",
  DropdownSingleSelect: "String",
};

export const toolboxDisplayNames = {
  cancer_survival: "Cancer Survival",
  data_fetching: "Data Fetching",
  plots: "Plots",
  stats: "Stats",
};

export const kebabCase = (str) => {
  return str
    .replace(/([a-z])([A-Z])/g, "$1-$2")
    .replace(/[\s_]+/g, "-")
    .toLowerCase();
};

export const snakeCase = (str) => {
  return str
    .replace(/([a-z])([A-Z])/g, "$1_$2")
    .replace(/[\s-]+/g, "_")
    .toLowerCase();
};

// https://discuss.codemirror.net/t/how-to-make-certain-ranges-readonly-in-codemirror6/3400/5
export function createReadOnlyTransactionFilter(readonlyRangeSet) {
  return () => {
    return EditorState.transactionFilter.of((tr) => {
      if (
        readonlyRangeSet &&
        tr.docChanged &&
        !tr.annotation(Transaction.remote)
      ) {
        let block = false;
        tr.changes.iterChangedRanges((chFrom, chTo) => {
          readonlyRangeSet.between(chFrom, chTo, (roFrom, roTo) => {
            if (chTo > roFrom && chFrom < roTo) block = true;
          });
        });
        if (block) return [];
      }
      return tr;
    });
  };
}

export const forcedAnnotation = Annotation.define();

// from: https://github.com/andrebnassis/codemirror-readonly-ranges/blob/master/src/lib/index.ts
export const preventModifyTargetRanges = (getReadOnlyRanges) =>
  // code mirror extension that
  // takes a function that returns read only ranges
  // and prevents modification on them
  EditorState.transactionFilter.of((tr) => {
    let readonlyRangeSet = getReadOnlyRanges(tr.startState);

    if (
      readonlyRangeSet &&
      tr.docChanged &&
      !tr.annotation(forcedAnnotation) &&
      !tr.annotation(Transaction.remote)
    ) {
      let block = false;
      tr.changes.iterChangedRanges((chFrom, chTo) => {
        readonlyRangeSet.between(chFrom, chTo, (roFrom, roTo) => {
          if (
            (chTo > roFrom && chFrom < roTo) ||
            // also prevent adding at the start or end of a readonly range
            chFrom === roTo ||
            chTo === roFrom
          )
            block = true;
        });
      });
      if (block) return [];
    }
    return tr;
  });

// breaks new lines, and split to max of maxLength characters
// first split on newlines
// then split on spaces
export function breakLinesPretty(str, maxLength = 60, indent = 1) {
  return str
    .split("\n")
    .map((line) => {
      return line
        .split(" ")
        .reduce((acc, word) => {
          if (
            acc.length &&
            acc[acc.length - 1].length + word.length < maxLength
          ) {
            acc[acc.length - 1] += " " + word;
          } else {
            acc.push(word);
          }
          return acc;
        }, [])
        .join("\n" + "  ".repeat(indent));
    })
    .join("\n" + "  ".repeat(indent));
}

export function createPythonFunctionInputString(inputDict, indent = 2) {
  return (
    "  ".repeat(indent) +
    inputDict.name +
    (inputDict.type ? ": " + inputDict.type : "") +
    "," +
    (inputDict.description ? " # " + inputDict.description : "")
  );
}

export function createYjsDocFromUint8Array(uint8Array) {
  const doc = new Doc();
  applyUpdate(doc, uint8Array);
  return doc;
}

export function createNewYjsXmlElement(nodeName, attributes) {
  const newElement = new XmlElement(nodeName);
  for (const [key, value] of Object.entries(attributes)) {
    newElement.setAttribute(key, value);
  }
  return newElement;
}

// inserting to a new blocknote doc using yjs
// newBlock = new Y.XmlElement("blockcontainer");
// newBlock.setAttribute("id", v4());
// newBlock.setAttribute("backgroundColor", "default");
// newBlock.setAttribute("textColor", "default");
// newAnalysis = new Y.XmlElement("analysis");
// newAnalysis.setAttribute("id", analysisId);
// newBlock.insert(0, [newAnalysis])
// doc = new Y.Doc()
// // get the uin8array of the doc from the backend table
// Y.applyUpdate(doc, arr)
// blockGroup = doc.getXmlFragment("document-store").firstChild
// blockGroup.insert(blockGroup.length, [newBlock])
// arr = Y.encodeStateAsUpdate(doc)
// // send arr to the backend to update the table
export function appendAnalysisToYjsDoc(yjsDoc, analysisId) {
  const newBlock = createNewYjsXmlElement("blockcontainer", {
    id: v4(),
    backgroundColor: "default",
    textColor: "default",
  });
  const newAnalysis = createNewYjsXmlElement("analysis", {
    analysisId: analysisId,
  });
  newBlock.insert(0, [newAnalysis]);

  // yjsD.emit("update", [encoder.toUint8Array(), transaction.origin, doc]);

  yjsDoc.transact((tr) => {
    const blockGroup = yjsDoc.getXmlFragment("document-store").firstChild;

    blockGroup.insert(blockGroup.length, [newBlock]);
    console.log(tr);
  });
  return true;
}

export function createInitialToolInputs(toolName, parentIds) {
  let initialInputs = {};

  // if there's a pandas dataframe type in the inputs, default that to the parent's output
  Object.values(toolsMetadata[toolName].input_metadata).forEach((inp) => {
    if (inp.type === "pandas.core.frame.DataFrame") {
      try {
        initialInputs[inp.name] = "global_dict." + parentIds?.[0];
      } catch (e) {
        console.log(e);
      }
    } else {
      initialInputs[inp.name] = Array.isArray(inp.default)
        ? inp.default[0]
        : inp.default;
    }
  });
  return initialInputs;
}

export function arrayOfObjectsToObject(arr, key, includeKeys = null) {
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

export function parseData(data_csv) {
  const data = csvParse(data_csv);
  const colNames = data.columns;
  const rows = data.map((d) => Object.values(d));

  const r = reFormatData(rows, colNames);

  // make sure we correctly render quantitative columns
  // if a column has numeric: true
  // convert all entires in all rows to number
  r.newCols.forEach((col, i) => {
    if (col.numeric) {
      r.newRows.forEach((row) => {
        row[col.title] = Number(row?.[col.title]);
      });
    }
  });

  return {
    columns: r.newCols,
    data: r.newRows,
  };
}

const addToolEndpoint = setupBaseUrl("http", "add_tool");
export const addTool = async ({
  tool_name,
  function_name,
  description,
  code,
  input_metadata,
  output_metadata,
  toolbox,
  no_code = false,
}) => {
  const payload = {
    tool_name,
    function_name,
    description,
    code,
    input_metadata,
    output_metadata,
    toolbox,
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

    const json = await res.json();
    return json;
  } catch (e) {
    console.error(e);
    return { success: false, error_message: e };
  }
};
