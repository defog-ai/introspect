import React from "react";
import dayjs from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat.js";
import weekOfYear from "dayjs/plugin/weekOfYear.js";
import advancedFormat from "dayjs/plugin/advancedFormat.js";
dayjs.extend(advancedFormat);
dayjs.extend(weekOfYear);
dayjs.extend(customParseFormat);

import { chartColors } from "../../context/ThemeContext";
import { Popover } from "antd";

export const questionModes = [
  [
    "Create a report",
    "What would you like a report on? Best for big picture, future-oriented questions from your data.",
    "Useful for asking broad questions from your data.",
  ],
  [
    "Query my data",
    "Ask a question to gather insights from your data",
    "Useful for asking specific, query-able questions from your data.",
  ],
].map((d) => ({
  value: d[0],
  label: (
    <Popover
      overlayClassName="agent-popover"
      overlayInnerStyle={{
        backgroundColor: "black",
      }}
      align={{ offset: [15, 0] }}
      content={<div style={{ width: "200px", color: "white" }}>{d[2]}</div>}
      placement="right"
    >
      <div className="agent-tool-option">{d[0]}</div>
    </Popover>
  ),
  placeholder: d[1],
}));

const dateFormats = [
  "YYYY-MM-DD HH:mm:ss",
  "YYYY-MM-DDTHH:mm:ss",
  "YYYY-MM-DD",
  "YYYY-MM",
];

export function isDate(s) {
  return dayjs(s, dateFormats, true).isValid();
  // return /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$/gi.test(s);
}

export function cleanString(s) {
  return String(s).toLowerCase().replace(/ /gi, "-");
}

// change float cols with decimals to 2 decimal places
export function roundColumns(data, columns) {
  const decimalCols = columns
    ?.filter((d) => d.colType === "decimal")
    .map((d) => d.key);

  // create new data by copying it deeply because we want to plot accurate vals in charts
  const roundedData = [];
  data?.forEach((d, i) => {
    roundedData.push(Object.assign({}, d));

    decimalCols?.forEach((colName) => {
      let x = roundedData[i][colName];
      // try to convert to a number
      if (+x || x === 0) {
        try {
          // round to two decimals
          return x.toFixed(2);
        } catch (e) {
          // set to null
          return null;
        }
      } else {
        return null;
      }
    });
  });

  return roundedData;
}

// sigh. sometimes model returns numbers as strings for some reason.
// so use regex instead of typeof
// from here: https://stackoverflow.com/questions/2811031/decimal-or-numeric-values-in-regular-expression-validation
function isNumber(input) {
  const regex1 = /^-?(0|[1-9]\d*)?(\.\d+)?$/;
  const regex2 = /\d$/;
  return regex1.test(input) && regex2.test(input);
}

function isExpontential(input) {
  const regex = /^-?(0|[1-9]\d*)?(\.\d+)?([eE][-+]?\d+)?$/;
  return regex.test(input);
}

export function inferColumnType(rows, colIdx, colName) {
  // go through rows
  const res = {};
  res["numeric"] = false;
  res["variableType"] = "quantitative";
  if (
    colName.endsWith("_id") ||
    colName.startsWith("id_") ||
    colName === "id"
  ) {
    res["colType"] = "string";
    res["variableType"] = "categorical";
    res["numeric"] = false;
    res["simpleTypeOf"] = typeof val;
    return res;
  } else if (/^year$/gi.test(colName) || /^month$/gi.test(colName)) {
    res["colType"] = "date";
    res["variableType"] = "categorical";
    res["numeric"] = false;
    res["simpleTypeOf"] = typeof val;
    return res;
  } else {
    for (let i = 0; i < rows.length; i++) {
      const val = rows[i][colIdx];
      if (val === null) continue;
      else if (isDate(val)) {
        res["colType"] = "date";
        res["variableType"] = "categorical";
        res["numeric"] = false;
      }
      // is a number and also has a decimal
      else if (isNumber(val) && val.toString().indexOf(".") >= 0) {
        res["colType"] = "decimal";
        res["numeric"] = true;
        res["variableType"] = "quantitative";
      }
      // if number but no decimal
      // or is exponential value
      else if (isNumber(val) || isExpontential(val)) {
        res["colType"] = "integer";
        res["numeric"] = true;
        res["variableType"] = "quantitative";
      } else {
        res["colType"] = typeof val;
        res["numeric"] = res["colType"] === "number";
        res["variableType"] =
          res["colType"] === "number" ? "quantitative" : "categorical";
      }

      res["simpleTypeOf"] = typeof val;
      return res;
    }
  }
}

function formatTime(val) {
  return dayjs(val, [
    ...dateFormats,
    ["YYYY", "MM", "MMM", "M", "MMMM"],
  ]).format("D MMM 'YY");
}

export function setChartJSDefaults(
  ChartJSRef,
  title = "",
  xAxisIsDate = false,
  theme,
  pieChart = false
) {
  ChartJSRef.defaults.scale.grid.drawOnChartArea = false;
  ChartJSRef.defaults.interaction.axis = "x";
  ChartJSRef.defaults.interaction.mode = "nearest";
  ChartJSRef.defaults.maintainAspectRatio = false;
  ChartJSRef.defaults.plugins.title.display = true;
  // pie charts can be multiple, so we don't want to show the overall title aka query
  // we want to show each column's title above each pie chart instead (this is done in the component itself)
  if (!pieChart) {
    ChartJSRef.defaults.plugins.title.text = title;
  }

  // tooltip background clor white
  ChartJSRef.defaults.plugins.tooltip.backgroundColor = "white";
  // title and label color is chartcolors primary color
  ChartJSRef.defaults.plugins.tooltip.titleColor = "#0D0D0D";
  ChartJSRef.defaults.plugins.tooltip.bodyColor = "#0D0D0D";
  // border color is defog blue
  ChartJSRef.defaults.plugins.tooltip.borderColor = "#2B59FF";
  ChartJSRef.defaults.plugins.tooltip.borderWidth = 1;
  ChartJSRef.defaults.plugins.tooltip.padding = 10;

  ChartJSRef.defaults.plugins.title.color = theme?.primaryText;

  // if x axis is a date, add a d3 formatter
  ChartJSRef.defaults.plugins.tooltip.displayColors = false;

  ChartJSRef.defaults.plugins.tooltip.callbacks.title = function (
    tooltipItems
  ) {
    return tooltipItems.map((item) =>
      xAxisIsDate ? formatTime(item.label) : item.label
    );
  };

  ChartJSRef.defaults.scales.category.ticks = {
    callback: function (value) {
      return xAxisIsDate
        ? formatTime(this.getLabelForValue(value))
        : this.getLabelForValue(value);
    },
  };

  ChartJSRef.defaults.plugins.tooltip.callbacks.label = function (tooltipItem) {
    return tooltipItem.dataset.label + ": " + tooltipItem.formattedValue;
  };

  if (pieChart) {
    // legend labels are also dates
    // pie/doughnuts charts are weird in chartjs
    // brilliant hack to edit some props of legendItems without having to remake them from here: https://stackoverflow.com/questions/39454586/pie-chart-legend-chart-js
    ChartJSRef.overrides.pie.plugins.legend.labels.filter = function (
      legendItem
    ) {
      legendItem.text = xAxisIsDate
        ? formatTime(legendItem.text)
        : legendItem.text;
      return true;
    };
  }
}

export const mapToObject = (
  map = new Map(),
  parentNestLocation = [],
  processValue = (d) => d,
  // hook will allow you to do extra computation on every recursive call to this function
  hook = () => {}
) =>
  Object.fromEntries(
    Array.from(map.entries(), ([key, value]) => {
      // also store nestLocation for all of the deepest children
      value.nestLocation = parentNestLocation.slice();
      value.nestLocation.push(key);
      hook(key, value);

      return value instanceof Map
        ? [key, mapToObject(value, value.nestLocation, processValue)]
        : [key, processValue(value)];
    })
  );

export function getColValues(data = [], columns = []) {
  if (!columns.length || !data || !data.length) return [];

  // if single column, just return that column value
  // if multiple, join the column values with separator
  const vals = new Set();
  data.forEach((d) => {
    const val = columns.reduce((acc, c, i) => {
      if (i > 0) {
        acc += "-";
      }
      acc += d[c];
      return acc;
    }, "");

    vals.add(val);
  });

  return Array.from(vals);
}

export function processData(data, columns) {
  // find if there's a date column
  const dateColumns = columns?.filter((d) => d.colType === "date");
  // date comes in as categorical column, but we use that for the x axis, so filter that out also
  const categoricalColumns = columns?.filter(
    (d) => d.variableType[0] === "c" && d.colType !== "date"
  );

  // y axis columns are only numeric non date columns
  const yAxisColumns = columns?.filter(
    (d) => d.variableType[0] !== "c" && d.colType !== "date"
  );

  const xAxisColumns = columns?.slice();

  // find unique values for each of the x axis columns for the dropdowns
  // this we'll use for "labels" prop for chartjs
  const xAxisColumnValues = {};
  xAxisColumns?.forEach((c) => {
    xAxisColumnValues[c.key] = getColValues(data, [c.key]);
  });

  return {
    xAxisColumns: xAxisColumns ? xAxisColumns : [],
    categoricalColumns: categoricalColumns ? categoricalColumns : [],
    yAxisColumns: yAxisColumns ? yAxisColumns : [],
    dateColumns: dateColumns ? dateColumns : [],
    xAxisColumnValues,
  };
}

export function isEmpty(obj) {
  for (const prop in obj) {
    if (Object.hasOwn(obj, prop)) {
      return false;
    }
  }

  return true;
}

export function sanitiseColumns(columns) {
  // check if it's not an array or undefined
  if (!Array.isArray(columns) || !columns) {
    return [];
  }
  // convert all existing columns to strings
  const cleanColumns = columns.map((c) => String(c));
  return cleanColumns;
}

export function sanitiseData(data) {
  // check if it's not an array or undefined
  if (!Array.isArray(data) || !data) {
    return [];
  }
  // filter out null elements from data array
  // for the remaining rows, check if the whole row is null
  const cleanData = data
    .filter((d) => d)
    .filter((d) => !d.every((val) => val === null));
  return cleanData;
}

export function createChartConfig(
  data,
  xAxisColumns,
  yAxisColumns,
  selectedXValues,
  xAxisIsDate
) {
  if (
    !xAxisColumns.length ||
    !yAxisColumns.length ||
    !selectedXValues ||
    !data ||
    !data.length
  ) {
    return {
      chartLabels: [],
      chartData: [],
    };
  }

  // chart labels are just selectedXValues
  const chartLabels = selectedXValues?.map((d) => d.label);

  // go through data and find data points for which the x value exists in chartLabels
  let filteredData = data.filter((d) => {
    const xLab = getColValues(
      [d],
      xAxisColumns.map((d) => d.label)
    )[0];

    d.__xLab__ = xLab;
    return chartLabels?.includes(xLab);
  });

  // if there's multiple data rows for an x axis label, sum all the yAxisColumns for them
  // this is the data that will be used for the chart
  // don't use d3 while doing this, since d3 is not imported in this file
  // use native js instead
  filteredData = filteredData.reduce((acc, curr) => {
    const key = curr.__xLab__;

    if (!acc[key]) {
      acc[key] = {};
      yAxisColumns.forEach((col) => {
        acc[key][col.label] = 0;
      });
    }

    yAxisColumns.forEach((col) => {
      acc[key][col.label] += curr[col.label];
    });
    return acc;
  }, {});

  // if x axis is not date,
  // sort labels and fitleredData by the first yAxisColumn
  if (!xAxisIsDate) {
    chartLabels?.sort(
      (a, b) =>
        filteredData[b][yAxisColumns[0].label] -
        filteredData[a][yAxisColumns[0].label]
    );
  }

  // convert filteredData to an array of objects
  // this is the format that chartjs expects
  filteredData = Object.entries(filteredData).map(([key, value]) => {
    const obj = { __xLab__: key };
    yAxisColumns.forEach((col) => {
      obj[col.label] = value[col.label];
    });
    return obj;
  });

  // use chartjs parsing to create chartData
  // for each yAxisColumn, there is a chartjs "dataset"
  const chartData = yAxisColumns?.map((col, i) => ({
    label: col.label,
    data: filteredData,
    backgroundColor: chartColors[i % chartColors.length],
    parsing: {
      xAxisKey: "__xLab__",
      yAxisKey: col.label,
      // for pie charts
      key: col.label,
    },
  }));
  return { chartData, chartLabels };
}

export function transformToCSV(rows, columnNames) {
  const header = '"' + columnNames.join('","') + '"\n';
  const body = rows.map((d) => '"' + d.join('","') + '"').join("\n");
  return header + body;
}

// https://stackoverflow.com/questions/24898044/is-possible-to-save-javascript-variable-as-file
export function download_csv(csvString) {
  var hiddenElement = document.createElement("a");

  hiddenElement.href = "data:attachment/text," + encodeURI(csvString);
  hiddenElement.target = "_blank";
  hiddenElement.download = `data-${new Date().toISOString().slice(0, -5)}.csv`;
  hiddenElement.click();
  hiddenElement.remove();
}

export const tools = [
  {
    // name: "SQL Aggregator",
    name: "Fetch data",
    description:
      // "Generates SQL queries to get aggregates (with splits on multiple attributes).Good for getting percentiles, summarizing quantities over time, topk rows and outliers based on percentiles, or joining information across tables. Not good at statistical analysis",
      "Fetch data from your database. Good for viewing outliers and subsets of your data. For analysis, try any of the other tools.",
    fn: "sql_aggregator",
  },
  {
    // name: "Summary Statistics",
    name: "Summarize data",
    description:
      // "Generates SQL + python code to sample and estimate summary statistics from a given column. Good for getting mean, std, p25, p50, p75",
      "Good for getting a brief overview of the data using simple statistics like averages, standard deviation, etc.",
    fn: "py_column_summarizer",
  },
  {
    // name: "Correlation Finder",
    name: "Find patterns",
    description:
      // "Generates python code to find correlations in the data. Good for finding correlations and associations between values in different columns. Not good when number of rows is large",
      "Finds patterns and relationships in your data. Note that performance is worse with large datasets.",
    fn: "py_correlator",
  },
  {
    // name: "Time Series Forecaster",
    name: "Predict trends",
    description: "Forecasts future trends in time series data.",
    fn: "py_time_series_forecaster",
  },
];

export const reFormatData = (data, columns) => {
  let newCols;
  let newRows;

  // if inferred typeof column is number, decimal, or integer
  // but simple typeof value is string, means it's a numeric value coming in as string
  // so coerce them to a number
  // store the indexes of such columns
  const numericAsString = [];
  // deal with columns like "username" etc coming in as numbers.
  // if inferred type is numeric but variable Type is "categorical"
  const stringAsNumeric = [];

  let validData = sanitiseData(data);
  let validColumns = sanitiseColumns(columns);

  if (validColumns.length && validData.length) {
    const cols = columns;
    const rows = validData;
    newCols = [];
    newRows = [];
    for (let i = 0; i < cols.length; i++) {
      newCols.push(
        Object.assign(
          {
            title: cols[i],
            dataIndex: cols[i],
            key: cols[i],
            // simple typeof. if a number is coming in as string, this will be string.
            simpleTypeOf: typeof rows[0][i],
            sorter:
              rows.length > 0 && typeof rows[0][i] === "number"
                ? (a, b) => a[cols[i]] - b[cols[i]]
                : (a, b) =>
                    String(a[cols[i]]).localeCompare(String(b[cols[i]])),
          },
          inferColumnType(rows, i, cols[i])
        )
      );
      if (newCols[i].numeric && newCols[i].simpleTypeOf === "string") {
        numericAsString.push(i);
      }
      if (
        newCols[i].numeric &&
        newCols[i].simpleTypeOf === "number" &&
        newCols[i].variableType === "categorical"
      ) {
        stringAsNumeric.push(i);
      }
    }

    for (let i = 0; i < rows.length; i++) {
      let row = {};
      row["key"] = i;
      row["index"] = i;

      for (let j = 0; j < cols.length; j++) {
        row[cols[j]] = rows[i][j];
      }
      newRows.push(row);
    }

    // push an index column
    newCols.push({
      title: "index",
      dataIndex: "index",
      key: "index",
      sorter: (a, b) => a["index"] - b["index"],
      colType: "integer",
      variableType: "integer",
      numeric: true,
      simpleTypeOf: "number",
    });
  } else {
    newCols = [];
    newRows = [];
  }

  return { newCols, newRows };
};

export const chartNames = {
  kmc: "Kaplan-Meier Curves",
  boxplot: "Boxplot",
  heatmap: "Heatmap",
};
