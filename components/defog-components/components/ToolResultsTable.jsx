import React, {
  isValidElement,
  Fragment,
  useEffect,
  useState,
  useMemo,
  useContext,
  useRef,
  useCallback,
} from "react";
import { Tabs, Table, Button, message, Popover } from "antd";
import ChartContainer from "./ChartContainer";
import {
  chartNames,
  processData,
  reFormatData,
  roundColumns,
} from "./common/utils";
import { FaRegCopy } from "react-icons/fa";

import {
  TableOutlined,
  BarChartOutlined,
  DownloadOutlined,
} from "@ant-design/icons";
import ErrorBoundary from "./common/ErrorBoundary";
import ChartImage from "./ChartImage";

import Editor from "react-simple-code-editor";
import { highlight, languages } from "prismjs/components/prism-core";

import "prismjs/components/prism-clike";
import "prismjs/components/prism-sql";
import "prismjs/components/prism-python";

import "prismjs/themes/prism.css";
import { roundNumber } from "../../../utils/utils";
import setupBaseUrl from "../../../utils/setupBaseUrl";

const downloadCsvEndpoint = setupBaseUrl("http", "download_csv");

// tabBarLeftContent: extra content for the tab bar on the left side
export function ToolResultsTable({
  toolRunId,
  analysisId,
  nodeId,
  tableData = null,
  codeStr = null,
  sql = null,
  chartImages = null,
  reactiveVars = null,
  handleEdit = () => {},
}) {
  const tableChartRef = useRef(null);
  const [sqlQuery, setSqlQuery] = useState(sql);
  const [toolCode, setToolCode] = useState(codeStr);
  const [csvLoading, setCsvLoading] = useState(false);

  async function saveCsv() {
    if (csvLoading) return;

    let csv = "";
    try {
      // tableData: {columns: Array(4), data: Array(1)}
      if (!tableData) return;
      const { columns, data } = tableData;

      // if data has >= 1000 rows, it might have been truncated
      // in this case, send a request to the server to get the full data
      // we will send the tool run id and also the output_storage_key we need to download
      if (data.length >= 1000) {
        setCsvLoading(true);

        const res = await fetch(downloadCsvEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            tool_run_id: toolRunId,
            output_storage_key: nodeId,
            analysis_id: analysisId,
          }),
        }).then((r) => r.json());

        if (!res?.success) {
          message.error(res?.error_message || "Error saving CSV.");
          return;
        } else if (res?.success && res?.csv) {
          csv = res.csv;
        }
      } else {
        const filteredColumns = columns.filter((d) => d.title !== "index");
        // Use columns to append to a string
        csv = filteredColumns.map((d) => d.title).join(",") + "\n";
        // Use data to append to a string
        // go through each row and each column and append to csv
        for (let i = 0; i < data.length; i++) {
          let row = data[i];
          for (let j = 0; j < filteredColumns.length; j++) {
            csv += row[filteredColumns[j].title];
            if (j < filteredColumns.length - 1) csv += ",";
          }
          csv += "\n";
        }
      }

      // Create a blob and download it
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      // name with time stamp but without miliseconds

      a.download = `${nodeId}-${new Date().toISOString().split(".")[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      // delete a tag
      a.remove();
      message.success("CSV saved.");
    } catch (e) {
      console.error(e);
      message.error("Error saving CSV.");
    } finally {
      setCsvLoading(false);
    }
  }

  let extraTabs = [];

  // if reactive vars change, add dragstart handler to them
  useEffect(() => {
    if (!tableChartRef.current) return;
    const reactiveEls = tableChartRef.current.getElementsByClassName(
      "table-chart-reactive-var"
    );

    Array.from(reactiveEls).forEach((el) => {
      el.ondragstart = (e) => {
        e.stopPropagation();
        e.dataTransfer.clearData();
        e.dataTransfer.setData(
          "text/html",
          `<reactive-var
              data-reactive-var='true'
              data-reactive-var-name=${el.dataset.reactiveVarName}
              data-val=${roundNumber(+el.dataset.val)}
              data-reactive-var-nest-location=${
                el.dataset.reactiveVarNestLocation
              }
              data-table-id=${el.dataset.toolRunId}>
            </reactive-var>`
        );
      };
    });
  }, [reactiveVars]);

  const updateCodeAndSql = (updateProp = null, newVal) => {
    // update values of the code and the SQL
    if (updateProp !== "sql" && updateProp !== "code") return;
    if (!toolRunId) return;
    if (!newVal) return;

    if (updateProp === "sql") {
      setSqlQuery(newVal);
    }
    if (updateProp === "code") {
      setToolCode(newVal);
    }
    handleEdit({
      tool_run_id: toolRunId,
      update_prop: updateProp,
      new_val: newVal,
    });
  };

  useEffect(() => {
    setSqlQuery(sql);
    setToolCode(codeStr);
  }, [sql, codeStr]);

  const results = useMemo(() => {
    // extra tabs should be an array and all elements should be jsx components
    if (
      !extraTabs ||
      !Array.isArray(extraTabs) ||
      !extraTabs.every((d) => d.component && d.tabLabel) ||
      !extraTabs.every((d) => isValidElement(d.component))
    ) {
      extraTabs = [];
    }

    let tabs = [];
    if (tableData) {
      const roundedData = roundColumns(tableData.data, tableData.columns);

      // find which dataset is the current node
      tabs.push({
        component: (
          <Table
            key="0"
            dataSource={roundedData}
            // don't show index column in table
            columns={tableData.columns.filter((d) => d.title !== "index")}
            // scroll={{ x: "max-content" }}
            size="small"
            pagination={{ pageSize: 8, showSizeChanger: false }}
          />
        ),
        tabLabel: "Table",
        icon: <TableOutlined />,
      });
    }

    if (!chartImages || chartImages.length <= 0) {
      if (tableData) {
        const {
          xAxisColumns,
          categoricalColumns,
          yAxisColumns,
          xAxisColumnValues,
          dateColumns,
        } = processData(tableData.data, tableData.columns);
        tabs.push({
          component: (
            <ErrorBoundary>
              <ChartContainer
                xAxisColumns={xAxisColumns}
                dateColumns={dateColumns}
                categoricalColumns={categoricalColumns}
                yAxisColumns={yAxisColumns}
                xAxisColumnValues={xAxisColumnValues}
                data={tableData.data}
                columns={tableData.columns}
                title={tableData.query}
                key="1"
                vizType={"Bar Chart"}
              ></ChartContainer>
            </ErrorBoundary>
          ),
          tabLabel: "Chart",
          icon: <BarChartOutlined />,
        });
      }
    } else {
      // if chartImagePath is present, load the image of the chart instead
      tabs.push({
        component: (
          <ErrorBoundary>
            <ChartImage images={chartImages} />
          </ErrorBoundary>
        ),
        tabLabel: chartNames[chartImages[0].type] || "Chart",
      });
    }
    if (sqlQuery !== null) {
      // show the sql query
      tabs.push({
        component: (
          <ErrorBoundary>
            <>
              <p>The following query was generated:</p>
              <Editor
                className="language-sql table-code-ctr"
                value={sqlQuery}
                highlight={(code) => {
                  return highlight(code, languages.sql, "sql");
                }}
                onValueChange={(newVal) => {
                  updateCodeAndSql("sql", newVal);
                }}
              />
            </>
          </ErrorBoundary>
        ),
        tabLabel: "SQL",
      });
    }

    if (toolCode !== null) {
      // show the codeStr query
      tabs.push({
        component: (
          <ErrorBoundary>
            <>
              <p>The following code was run:</p>
              <Editor
                className="language-python table-code-ctr"
                value={toolCode}
                highlight={(code) => {
                  return highlight(code, languages.python, "python");
                }}
                onValueChange={(newVal) => updateCodeAndSql("code", newVal)}
              />
            </>
          </ErrorBoundary>
        ),
        tabLabel: "Code",
      });
    }

    // push extra tabs
    tabs = tabs.concat(extraTabs);

    // convert to antd tabs
    tabs = (
      <Tabs
        tabBarExtraContent={{
          right: (
            <Button
              onClick={async () => {
                await saveCsv();
              }}
              size="small"
              title="Download CSV"
              loading={csvLoading}
              disabled={csvLoading}
            >
              <DownloadOutlined />
            </Button>
          ),
        }}
        defaultActiveKey={!chartImages || !chartImages.length ? "0" : "1"}
        items={tabs.map((d, i) => ({
          key: String(i),
          label: (
            <span>
              {d.icon ? d.icon : null}
              {d.tabLabel ? d.tabLabel : `Tab-${i}`}
            </span>
          ),
          children: d.component,
        }))}
      ></Tabs>
    );

    return tabs;
  }, [tableData, extraTabs, chartImages, toolCode, sqlQuery]);

  const reactiveVarJsx = useMemo(() => {
    if (
      !reactiveVars ||
      typeof reactiveVars !== "object" ||
      Object.keys(reactiveVars).length <= 0
    )
      return <></>;

    if (
      reactiveVars &&
      typeof reactiveVars === "object" &&
      Object.keys(reactiveVars).length > 0
    ) {
      // keep nesting into divs until we get to the keys that are not objects

      let keys = Object.keys(reactiveVars);

      function nestedDivsUntilNumericKeys(key, obj, nestLocation) {
        if (typeof obj[key] === "object") {
          return (
            <div className="table-chart-reactive-var-group" key={key}>
              <>
                <div className="table-chart-reactive-var-group-name">{key}</div>
                <div className="table-chart-reactive-var-vals">
                  {Object.keys(obj[key]).map((nestedKey) =>
                    nestedDivsUntilNumericKeys(
                      nestedKey,
                      obj[key],
                      nestLocation + "---" + nestedKey
                    )
                  )}
                </div>
              </>
            </div>
          );
        }

        return (
          <div
            className="table-chart-reactive-var"
            key={key}
            data-reactive-var-name={key}
            data-val={obj[key]}
            data-reactive-var-nest-location={nestLocation}
            data-table-id={toolRunId}
            draggable="true"
          >
            <span className="reactive-var-name">{key}</span>
            <Popover
              content={() => <span>{obj[key]}</span>}
              rootClassName="reactive-var-popover-val"
              arrow={false}
              placement="left"
            >
              <span
                className="reactive-var-value"
                onClick={() => {
                  let clipboardItem = new ClipboardItem({
                    "text/html": new Blob(
                      [
                        `<reactive-var
                                data-reactive-var='true'
                                data-reactive-var-name=${key}
                                data-val=${roundNumber(+obj[key])}
                                data-reactive-var-nest-location=${nestLocation}
                                data-table-id=${toolRunId}>
                              </reactive-var>&nbsp;`,
                      ],
                      { type: "text/html" }
                    ),
                  });

                  navigator.clipboard.write([clipboardItem]).then(() => {
                    message.success("Copied to clipboard.");
                  });
                }}
              >
                {roundNumber(obj[key])}
              </span>
              <FaRegCopy
                className="reactive-var-copy-icon"
                title="Copy"
                onClick={() => {
                  let clipboardItem = new ClipboardItem({
                    "text/html": new Blob(
                      [
                        `<reactive-var
                                data-reactive-var='true'
                                data-reactive-var-name=${key}
                                data-val=${roundNumber(+obj[key])}
                                data-reactive-var-nest-location=${nestLocation}
                                data-table-id=${toolRunId}>
                              </reactive-var>&nbsp;`,
                      ],
                      { type: "text/html" }
                    ),
                  });

                  navigator.clipboard.write([clipboardItem]).then(() => {
                    message.success("Copied to clipboard.");
                  });
                }}
              />
            </Popover>
          </div>
        );
      }

      return (
        <>
          <div className="table-chart-reactive-var-ctr">
            <div className="sticky">
              <p className="small">STATISTICS</p>
              {keys.map((key) =>
                nestedDivsUntilNumericKeys(key, reactiveVars, key)
              )}
            </div>
          </div>
        </>
      );
    }
  }, [reactiveVars]);

  return (
    <div className="table-chart-ctr" ref={tableChartRef}>
      {results}
      {reactiveVarJsx}
    </div>
  );
}
