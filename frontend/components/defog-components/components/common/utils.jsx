import React from "react";
import dayjs from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat.js";
import weekOfYear from "dayjs/plugin/weekOfYear.js";
import advancedFormat from "dayjs/plugin/advancedFormat.js";
import isoWeek from "dayjs/plugin/isoWeek";
dayjs.extend(advancedFormat);
dayjs.extend(weekOfYear);
dayjs.extend(customParseFormat);
dayjs.extend(isoWeek);

import { chartColors } from "../../context/ThemeContext";
import { mean } from "d3-array";

const dateFormats = [
  "YYYY-MM-DD HH:mm:ss",
  "YYYY-MM-DDTHH:mm:ss",
  "YYYY-MM-DD",
  "YYYY-MM",
  "YYYY-MMM",
];

export function checkIfDate(s, colIdx, colName, rows) {
  // test if it's a date column
  // if it's == year or month or date
  // or if it contains year, month or date somewhere in the name

  let isDate =
    // either neat date
    dayjs(s, dateFormats, true).isValid() ||
    // or hacky date >.<
    /^year$/gi.test(colName) ||
    /^month$/gi.test(colName) ||
    /^date$/gi.test(colName) ||
    /^week$/gi.test(colName) ||
    /year/gi.test(colName) ||
    /month/gi.test(colName) ||
    /date/gi.test(colName) ||
    /week/gi.test(colName);

  // now to actually guess the date format
  let dateType, parseFormat;
  let dateToUnix = (val) => val;

  if (isDate) {
    // find out what it matches
    if (/^year$/gi.test(colName) || /year/gi.test(colName)) dateType = "year";
    if (/^month$/gi.test(colName) || /month/gi.test(colName))
      dateType = "month";
    if (/^date$/gi.test(colName) || /date/gi.test(colName)) dateType = "date";
    if (/^week$/gi.test(colName) || /week/gi.test(colName)) dateType = "week";

    // if it matches something, find what is the format
    if (dateType === "week") {
      // week should mean it's a week of the year so it should be a number from 1->52
      // it can either be integers or strings
      dateToUnix = (val) => dayjs().week(+val).unix();
      parseFormat = "W-YYYY";
    }
    if (dateType === "year") {
      // year should be a 4 digit number
      // first convert it to all numbers, and add month to it
      dateToUnix = (val) => dayjs("1-" + +val, "M-YYYY").unix();

      parseFormat = "M-YYYY";
    }
    if (dateType === "month") {
      // month can either be a 1 or 2 digit number or a string of month name
      // check from the rows which it is
      for (let i = 0; i < rows.length; i++) {
        let val = rows[i][colIdx];
        if (!val) continue;

        if (typeof val === "number") {
          // add current year to it for parsing
          dateToUnix = (val) =>
            dayjs(val + "-" + new Date().getFullYear(), "M-YYYY").unix();
          parseFormat = "M-YYYY";
        } else {
          // if it's a string
          // then check if it has alphabets
          const maybeMonthName = /[a-zA-Z]/.test(val);
          if (maybeMonthName) {
            // check length
            if (val.length > 3) {
              // if it's more than 3, it's a full month name
              dateToUnix = (val) => dayjs(val, "MMMM").unix();
              parseFormat = "MMMM";
            } else {
              // if it's less than equal to 3, it's probably a short month name
              dateToUnix = (val) => dayjs(val, "MMM").unix();
              parseFormat = "MMM";
            }
          } else {
            // is just month number
            // add current year to it for parsing
            dateToUnix = (val) =>
              dayjs(val + "-" + new Date().getFullYear(), "M-YYYY").unix();
            parseFormat = "M-YYYY";
          }
        }

        // only check the first non null value
        break;
      }
    }

    if (dateType === "date") {
      // we assume dayjs will be able to parse it
      dateToUnix = (val) => dayjs(val).unix();
      parseFormat = null;
    }
  } else {
    dateToUnix = (val) => val;
    parseFormat = null;
    dateType = null;
    isDate = false;
  }

  return { isDate, dateType, parseFormat, dateToUnix };
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
      try {
        // round to two decimals if number is greater than 1e-2, if not round to up to 6 decimal places
        if (Math.abs(x) > 1e-2) {
          roundedData[i][colName] = Math.round(x * 1e2) / 1e2;
        } else {
          roundedData[i][colName] = Math.round(x * 1e6) / 1e6;
        }
      } catch (e) {
        // set to null
        console.log(e);
        roundedData[i][colName] = x;
      }
    });
  });

  return roundedData;
}

// sigh. sometimes model returns numbers as strings for some reason.
// so use regex instead of typeof
// from here: https://stackoverflow.com/questions/2811031/decimal-or-numeric-values-in-regular-expression-validation
function isNumber(input) {
  // This regex matches a string that is a valid number with an optional % sign at the end.
  const regex = /^-?(0|[1-9]\d*)?(\.\d+)?%?$/;

  // Check if the input ends with a digit or a % sign, ensuring it's a number or a percentage
  const endsWithDigitOrPercent = /\d%?$/.test(input);

  return regex.test(input) && endsWithDigitOrPercent;
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
    res["simpleTypeOf"] = "string";
    return res;
  } else {
    // look at the first non-null row and guess the type
    for (let i = 0; i < rows.length; i++) {
      const val = rows[i][colIdx];
      if (val === null) continue;

      const dateCheck = checkIfDate(val, colIdx, colName, rows);
      if (dateCheck.isDate) {
        res["colType"] = "date";
        res["variableType"] = "categorical";
        res["numeric"] = false;
        res["parseFormat"] = dateCheck.parseFormat;
        res["dateToUnix"] = dateCheck.dateToUnix;
        res["dateType"] = dateCheck.dateType;
        res["isDate"] = dateCheck.isDate;
      }
      // is a number and also has a decimal
      else if (isNumber(val) && val.toString().indexOf(".") >= 0) {
        res["colType"] = "decimal";
        res["numeric"] = true;
        res["variableType"] = "quantitative";
        try {
          // get the mean of this column
          res["mean"] = mean(rows, (d) => d[colIdx]);
        } catch (e) {
          // do nothing
        }
      }
      // if number but no decimal
      // or is exponential value
      else if (isNumber(val) || isExpontential(val)) {
        res["colType"] = "integer";
        res["numeric"] = true;
        res["variableType"] = "quantitative";
        // get the mean of this column
        res["mean"] = mean(rows, (d) => d[colIdx]);
      } else {
        res["colType"] = typeof val;
        res["numeric"] = res["colType"] === "number";
        res["variableType"] =
          res["colType"] === "number" ? "quantitative" : "categorical";

        // if it's a number, get the mean
        if (res["numeric"]) {
          try {
            // get the mean of this column
            res["mean"] = mean(rows, (d) => d[colIdx]);
          } catch (e) {
            // do nothing
          }
        }
      }

      res["simpleTypeOf"] = typeof val;
      // just return. so we don't look at any further than the first non-null row
      return res;
    }
  }
}

function formatTime(val) {
  const toTitleCase = (str) => {
    return str.replace(/\w\S*/g, function (txt) {
      return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
  };

  // convert all values to date
  val = toTitleCase(val);
  // check if it matches any of the date formats
  const date = dayjs(val, dateFormats, true);
  if (date.isValid()) {
    return date.format("D MMM 'YY");
  } else {
    return val;
  }

  // dayjs(val, [...dateFormats, ["YYYY", "MM", "MMM", "M", "MMMM"]]).format(
  //   "D MMM 'YY",
  // );
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

// converts a Map into an Object.
// recursive function that can handle nested Maps as well.
// processValue is a function that can be used to process the value of each value in the resulting object
// hook is a function that can be used to do extra computation before we process a key, value pair
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
    (d) => d?.variableType?.[0] === "c" && d.colType !== "date"
  );

  // y axis columns are only numeric non date columns
  const yAxisColumns = columns?.filter(
    (d) => d?.variableType?.[0] !== "c" && d.colType !== "date"
  );

  const xAxisColumns = columns?.slice();

  // find unique values for each of the x axis columns for the dropdowns
  // this we'll use for "labels" prop for chartjs
  const xAxisColumnValues = {};
  xAxisColumns?.forEach((c) => {
    xAxisColumnValues[c.key] = getColValues(data, [c.key]);
  });

  const cleanedData = sanitiseData(data, true);

  return {
    xAxisColumns: xAxisColumns ? xAxisColumns : [],
    categoricalColumns: categoricalColumns ? categoricalColumns : [],
    yAxisColumns: yAxisColumns ? yAxisColumns : [],
    dateColumns: dateColumns ? dateColumns : [],
    xAxisColumnValues,
    data: cleanedData,
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

export function sanitiseData(data, chart = false) {
  // check if it's not an array or undefined
  if (!Array.isArray(data) || !data) {
    return [];
  }

  // filter out null elements from data array
  // for the remaining rows, check if the whole row is null
  let cleanData;
  if (!chart) {
    cleanData = data
      .filter((d) => d)
      .filter((d) => !d.every((val) => val === null));
  } else {
    cleanData = data;

    // remove percentage signs from data
    cleanData.forEach((d) => {
      Object.entries(d).forEach(([key, value]) => {
        if (typeof value === "string" && value.endsWith("%")) {
          d[key] = +value.slice(0, -1);
        }
      });
    });
  }
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
  } else {
    const colDetails = xAxisColumns[0].__data__;

    const dateToUnix = colDetails?.dateToUnix || ((d) => d);
    // if we do, then run the dateToUnix function on each label
    chartLabels.sort((a, b) => dateToUnix(a) - dateToUnix(b));
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

  if (xAxisIsDate) {
    // sort filtered data according to the labels
    filteredData.sort((a, b) => {
      if (xAxisIsDate) {
        return (
          chartLabels.indexOf(a.__xLab__) - chartLabels.indexOf(b.__xLab__)
        );
      }
    });
  }

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
  // deal with columns like "user_id" etc coming in as numbers.
  // if inferred type is numeric but variable Type is "categorical"
  const stringAsNumeric = [];

  let validData = sanitiseData(data, false);
  let validColumns = sanitiseColumns(columns);

  if (validColumns.length && validData.length) {
    const cols = columns;
    const rows = validData;
    newCols = [];
    newRows = [];
    for (let i = 0; i < cols.length; i++) {
      let inferredColumnType = inferColumnType(rows, i, cols[i]);
      let newCol = Object.assign({
        title: cols[i],
        dataIndex: cols[i],
        key: cols[i],
        // simple typeof. if a number is coming in as string, this will be string.
        simpleTypeOf: typeof rows[0][i],
        sorter:
          rows.length > 0 && typeof rows[0][i] === "number"
            ? (a, b) => a[cols[i]] - b[cols[i]]
            : rows.length > 0 && !isNaN(rows[0][i])
              ? (a, b) => Number(a[cols[i]]) - Number(b[cols[i]])
              : (a, b) => String(a[cols[i]]).localeCompare(String(b[cols[i]])),
        render: (value) => {
          if (typeof value === "number" || !isNaN(value)) {
            // don't add commas in dates (years can be 2020, 2021 etc.)
            if (inferredColumnType.isDate) {
              return value;
            } else {
              return Number(value).toLocaleString();
            }
          } else {
            return value;
          }
        },
        ...inferredColumnType,
      });

      newCols.push(newCol);
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
        if (numericAsString.indexOf(j) >= 0) {
          row[cols[j]] = rows[i][j];
        } else if (stringAsNumeric.indexOf(j) >= 0) {
          row[cols[j]] = "" + rows[i][j];
        } else row[cols[j]] = rows[i][j];
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
      mean: (newRows?.length + 1) / 2 || null,
    });
  } else {
    newCols = [];
    newRows = [];
  }

  return { newCols, newRows };
};

export const sentenceCase = (str) => {
  if (!str) return "";
  return str[0].toUpperCase() + str.slice(1);
};

export const chartNames = {
  kmc: "Kaplan-Meier Curves",
  boxplot: "Boxplot",
  heatmap: "Heatmap",
};
