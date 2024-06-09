import { Select } from "antd";
import React, { useEffect, useState, useRef, Fragment } from "react";
import {
  cleanString,
  createChartConfig,
  getColValues,
  isEmpty,
} from "./common/utils";
import PieChart from "./Charts/PieChart";
import ColumnChart from "./Charts/ColumnChart";
import TrendChart from "./Charts/TrendChart";
import styled from "styled-components";

function arrToAntD(arr, labelProp = "key", valueProp = "key") {
  return arr.map((d) => ({
    label: labelProp ? d?.[labelProp] : d,
    value: valueProp ? d?.[valueProp] : d,
    __data__: d,
  }));
}

const nullChartConfig = { chartLabels: [], chartData: [] };
const sizeThresh = 400;

export default function ChartContainer({
  xAxisColumns,
  dateColumns,
  yAxisColumns,
  xAxisColumnValues,
  data,
  title,
  vizType,
  theme,
}) {
  function createColumnValueOpts(col) {
    const colName = col.key;
    if (!xAxisColumnValues[colName]) {
      return [];
    }

    const opts = xAxisColumnValues[colName].map((d) => ({
      label: d,
      value: col.colType === "string" ? cleanString(d) : d,
    }));

    // add a "Select all option"
    // we will default to all selected if length is below threshols
    opts.unshift({
      label: opts.length > sizeThresh ? "Select All" : "Deselect-all",
      value: opts.length > sizeThresh ? "select-all" : "deselect-all",
    });
    return opts;
  }

  // convert x axis column values to antd's select options
  const xAxisOpts = useRef(
    xAxisColumns.reduce((obj, col) => {
      const colName = col.key;
      obj[colName] = createColumnValueOpts(col);
      return obj;
    }, {})
  );

  // Dropdowns:
  // X Axis: multi select. All columns.
  // Y Axis: multi select. All columns.
  // Other dropdowns based on the X axis selection. Using categorical columns xAxisOpts above.

  const [xAxis, setXAxis] = useState(
    arrToAntD([dateColumns.length > 0 ? dateColumns[0] : xAxisColumns[0]])
  );

  const [yAxis, setYAxis] = useState(arrToAntD([yAxisColumns[0]]));

  const xAxisLabel = !xAxis.length
    ? undefined
    : xAxis.map((d) => d.label).join("-");
  // create dropdowns for selected column(s) for the x axis
  const xAxisOptValues = !xAxisLabel ? [] : xAxisOpts.current[xAxisLabel];

  const [selectedXValues, setSelectedXValues] = useState(
    !xAxisLabel
      ? {}
      : {
          [xAxisLabel]:
            xAxisColumnValues[xAxisLabel]?.length > sizeThresh
              ? [xAxisOpts.current[xAxisLabel]?.[1]]
              : xAxisOpts.current[xAxisLabel].length === 0
                ? []
                : [{ label: "All", value: "all-selected" }],
        }
  );

  // chart data
  const [chartConfig, setChartConfig] = useState(nullChartConfig);

  const xAxisDropdown = (
    <div className="chart-container-select">
      <h4>X Axis</h4>
      <Select
        mode="multiple"
        options={arrToAntD(xAxisColumns)}
        value={xAxis}
        placeholder="Select X Axis"
        onChange={(_, sel) => {
          if (sel.length === 0) {
            setSelectedXValues({});
            setXAxis(sel);
            return;
          }

          const selLabel = sel.map((d) => d.label).join("-");
          // if this exists in xAxisColumnValues, use it
          if (!xAxisColumnValues[selLabel]) {
            xAxisColumnValues[selLabel] = getColValues(
              data,
              sel.map((d) => d.label)
            );
            // create column options
            // if this doesn't exist, it's probably a multi column selection
            // we will coerce it to a string anyway. hence colType = "string"
            xAxisOpts.current[selLabel] = createColumnValueOpts({
              key: selLabel,
              colType: "string",
            });
          } else {
            // if less than size thresh
            // reset first option to select all
            if (xAxisColumnValues[selLabel].length > sizeThresh) {
              xAxisOpts.current[selLabel][0].label = "Select All";
              xAxisOpts.current[selLabel][0].value = "select-all";
            } else {
              xAxisOpts.current[selLabel][0].label = "Deselect All";
              xAxisOpts.current[selLabel][0].value = "deselect-all";
            }
          }

          setSelectedXValues({
            [selLabel]:
              xAxisOpts.current[selLabel].length > sizeThresh
                ? [xAxisOpts.current[selLabel][1]]
                : xAxisOpts.current[selLabel].length === 0
                  ? []
                  : [{ label: "All", value: "all-selected" }],
          });

          setXAxis(sel);
        }}
      ></Select>
    </div>
  );

  const yAxisDropdown = (
    <div className="chart-container-select">
      <h4>Y Axis</h4>
      <Select
        mode="multiple"
        options={arrToAntD(yAxisColumns)}
        defaultValue={yAxis}
        onChange={(_, sel) => {
          setYAxis(sel);
        }}
        placeholder="Select Y Axis"
      ></Select>
    </div>
  );

  const xAxisValuesDropdown =
    xAxisLabel === "" || !xAxisLabel ? (
      <></>
    ) : (
      // key force rerender when we change selectall->deselctall or vice versa
      <div key={xAxisOptValues?.[0]?.label} className="chart-container-select">
        <h4>{xAxisLabel}</h4>
        <Select
          mode="multiple"
          options={xAxisOptValues}
          defaultValue={selectedXValues[xAxisLabel]}
          value={selectedXValues[xAxisLabel]}
          placeholder={`Select ${xAxisLabel} to plot`}
          // allow select all
          showSearch={true}
          onChange={(_, sel) => {
            if (!xAxisOptValues.length) {
              return;
            }

            const newVals = {};
            // if select all is selected, select all options
            if (sel.findIndex((d) => d.value === "select-all") !== -1) {
              // set this column to a new option "all-selected"
              newVals[xAxisLabel] = [{ label: "All", value: "all-selected" }];
              // change "select all" to "deselect all"
              xAxisOptValues[0].label = "Deselect All";
              xAxisOptValues[0].value = "deselect-all";
            }
            // handle deselect all
            else if (sel.findIndex((d) => d.value === "deselect-all") !== -1) {
              // remove all options for this column
              newVals[xAxisLabel] = [];
              // change "deselect all" to "select all"
              xAxisOptValues[0].label = "Select All";
              xAxisOptValues[0].value = "select-all";
            } else {
              // change "deselect all" to "select all"
              xAxisOptValues[0].label = "Select All";
              xAxisOptValues[0].value = "select-all";
              // The temporary "all" option created above shows up as an empty object in the selected values
              // so we filter it out
              newVals[xAxisLabel] = sel.filter(
                (d) => !isEmpty(d) && d.value !== "all-selected"
              );
            }

            setSelectedXValues(Object.assign({}, selectedXValues, newVals));
          }}
        ></Select>
      </div>
    );

  const chartTypes = arrToAntD(
    ["Bar Chart", "Pie Chart", "Line Chart"],
    null,
    null
  );

  const [chartType, setChartType] = useState({
    label: vizType,
    value: vizType,
    __data__: vizType,
  });

  const chartTypeDropdown = (
    <div className="chart-container-select">
      <h4>Chart Type</h4>
      <Select
        mode="single"
        options={chartTypes}
        value={chartType}
        onChange={(_, sel) => {
          setChartType(sel);
        }}
      ></Select>
    </div>
  );

  const xAxisIsDate =
    xAxis.length === 1 && xAxis[0].__data__?.colType === "date";

  let chart = null;
  const chartProps = {
    chartConfig,
    title,
    xAxisIsDate,
    height: 400,
    theme,
  };

  switch (chartType.label) {
    case "Bar Chart":
      chart = (
        <ColumnChart
          // provide key otherwise chartjs defaults won't refresh
          key={title + xAxisIsDate}
          {...chartProps}
        />
      );
      break;
    case "Pie Chart":
      chart = <PieChart key={title + xAxisIsDate} {...chartProps} />;
      break;
    case "Line Chart":
    default:
      chart = <TrendChart key={title + xAxisIsDate} {...chartProps} />;
      break;
  }

  // change chart data
  useEffect(() => {
    if (
      !xAxis.length ||
      !yAxis.length ||
      !selectedXValues[xAxisLabel]?.length
    ) {
      setChartConfig(nullChartConfig);
      return;
    }

    setChartConfig(
      createChartConfig(
        data,
        xAxis,
        yAxis,
        selectedXValues[xAxisLabel].findIndex(
          (d) => d.value === "all-selected"
        ) > -1
          ? xAxisOptValues?.slice(1)
          : selectedXValues[xAxisLabel],
        xAxisIsDate
      )
    );
  }, [selectedXValues, xAxis, yAxis]);

  const errorMessages = {
    noCols:
      "There seem to be no plottable columns in your data. Is this a mistake? Please contact us!",
    noData: "No data to plot",
    noDataSelected: "Select data to plot.",
    noColsSelected: "Select both X and Y axis to plot.",
  };

  return (
    <ChartContainerWrap theme={theme}>
      <div className="chart-container">
        {!xAxisColumns.length || !yAxisColumns.length || !data.length ? (
          <div className="chart-error">
            <span>
              {!data.length ? errorMessages.noData : errorMessages.noCols}
            </span>
          </div>
        ) : (
          <>
            <div className="chart-container-controls">
              {chartTypeDropdown}
              {xAxisDropdown}
              {yAxisDropdown}
              {xAxisValuesDropdown}
            </div>

            {xAxisColumns.length &&
            yAxisColumns.length &&
            xAxis.length &&
            yAxis.length &&
            chartConfig.chartData?.length &&
            selectedXValues[xAxisLabel]?.length ? (
              <div className="chart">{chart}</div>
            ) : !xAxis.length || !yAxis.length ? (
              <div className="chart-error">
                <span>{errorMessages.noColsSelected}</span>
              </div>
            ) : (
              <div className="chart-error">
                <span>{errorMessages.noDataSelected}</span>
              </div>
            )}
          </>
        )}
      </div>
    </ChartContainerWrap>
  );
}

const ChartContainerWrap = styled.div`
  .chart-container {
    max-width: 100%;
    .chart-container-controls {
      display: flex;
      flex-wrap: wrap;

      .chart-container-select {
        margin: 10px 15px;
        width: 300px;
        .ant-select {
          width: 100%;
        }
        .ant-select-multiple {
          .ant-select-selection-item {
            background: #efefef;
          }
        }

        h4 {
          color: ${(props) =>
            props.theme ? props.theme.primaryText : "#606060"};
          margin-bottom: 2px;
        }
      }
    }
    .chart-error {
      width: 100%;
      height: 200px;
      display: flex;
      justify-content: center;
      align-items: center;
      span {
        color: ${(props) =>
          props.theme ? props.theme.secondaryText : "#606060"};
      }
    }
  }
`;
