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

import { TableOutlined, BarChartOutlined } from "@ant-design/icons";
import ErrorBoundary from "./common/ErrorBoundary";
import ChartImage from "./ChartImage";

import Editor from "react-simple-code-editor";
import { highlight, languages } from "prismjs/components/prism-core";

import "prismjs/components/prism-clike";
import "prismjs/components/prism-sql";
import "prismjs/components/prism-python";

import "prismjs/themes/prism.css";
import AgentLoader from "./common/AgentLoader";
import Lottie from "lottie-react";

import LoadingLottie from "./svg/loader.json";
import { ThemeContext, lightThemeColor } from "../context/ThemeContext";
import { ReactiveVariablesContext } from "../../docs/ReactiveVariablesContext";
import { setupWebsocketManager } from "../../../utils/websocket-manager";
import setupBaseUrl from "../../../utils/setupBaseUrl";
import { getTableData, roundNumber } from "../../../utils/utils";

// tabBarLeftContent: extra content for the tab bar on the left side
export function TableChart({
  tableId,
  tabBarLeftContent = null,
  analysisData,
}) {
  const [response, setResponse] = useState(null);
  const [tableData, setTableData] = useState(null);
  const [socketManager, setSocketManager] = useState(null);
  const [sql, setSql] = useState(null);
  const [codeStr, setCodeStr] = useState(null);
  const [reRunning, setReRunning] = useState(false);
  const [reactiveVars, setReactiveVars] = useState(null);
  const reactiveContext = useContext(ReactiveVariablesContext);
  const tableChartRef = useRef(null);

  const setStates = useCallback(
    (newTableData) => {
      if (!newTableData) return;
      const colNames = newTableData.data_csv.split("\n")[0].split(",");
      const rows = newTableData.data_csv
        .split("\n")
        .slice(1)
        .map((d) => d.split(","));

      const r = reFormatData(rows, colNames);

      setResponse({
        columns: r.newCols,
        data: r.newRows,
      });

      setTableData(newTableData);
      setSql(newTableData.sql);
      setCodeStr(newTableData.code);
      if (!newTableData.reactive_vars) return;

      setReactiveVars(newTableData.reactive_vars);
      Object.defineProperty(newTableData.reactive_vars, "analysisData", {
        get() {
          return analysisData;
        },
      });

      reactiveContext.update((prev) => {
        return {
          ...prev,
          [tableId]: newTableData.reactive_vars,
        };
      });
    },
    [reactiveContext.val, tableId]
  );

  // useEffect(() => {
  //   if (!reactiveVars) return;
  //   Object.defineProperty(newTableData.reactive_vars, "analysisData", {
  //     get() {
  //       return analysisData;
  //     },
  //   });

  //   reactiveContext.update((prev) => {
  //     return {
  //       ...prev,
  //       [tableId]: newTableData.reactive_vars,
  //     };
  //   });
  // }, [analysisData]);

  let extraTabs = [];

  function onMessage(msg) {
    console.log(msg);
    const res = JSON.parse(msg.data);
    console.log("Ran again response", res);
    if (!res.success) {
      if (res.error_message) {
        message.error("Failed with error: " + res.error_message);
      }
      setReRunning(false);
      return;
    }

    setStates(res.table_data);
    message.success("Ran again successfully.");
    setReRunning(false);
  }

  useEffect(() => {
    // on first render, connect to the backend, to get/send the latest

    async function setupSocket() {
      try {
        // check if agents_endpoint variable contains the string localhost
        // if it does, then we are running locally, so use ws instead of wss
        const urlToConnect = setupBaseUrl("ws", "table_chart");
        const mgr = await setupWebsocketManager(urlToConnect, onMessage);
        setSocketManager(mgr);
        let tableData = await getTableData(tableId);
        if (!tableData.success) return;
        tableData = tableData.table_data;

        setStates(tableData);
      } catch (e) {
        console.log(e);
      }
    }
    setupSocket();
  }, [tableId]);

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
            data-table-id=${el.dataset.tableId}>
          </reactive-var>`
        );
      };
    });
  }, [reactiveVars]);

  const updateCodeAndSql = (updateProp = null, newVal) => {
    // update values of the code and the SQL
    if (updateProp !== "sql" && updateProp !== "code") return;
    if (!socketManager) return;
    if (!tableId) return;
    if (!newVal) return;

    if (updateProp === "sql") {
      setSql(newVal);
    }
    if (updateProp === "code") {
      setCodeStr(newVal);
    }

    setTableData((prev) => {
      return {
        ...prev,
        [updateProp]: newVal,
        edited: true,
      };
    });
  };

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
    if (!tableData || !response) {
      return (
        <ThemeContext.Provider
          value={{ theme: { type: "light", config: lightThemeColor } }}
        >
          <AgentLoader
            message={"Loading table"}
            lottie={<Lottie animationData={LoadingLottie} loop={true} />}
          />
        </ThemeContext.Provider>
      );
    }
    const roundedData = roundColumns(response.data, response.columns);
    const chartImages = tableData.chart_images;
    let tabs = [
      {
        component: (
          <Table
            key="0"
            dataSource={roundedData}
            // don't show index column in table
            columns={response.columns.filter((d) => d.title !== "index")}
            // scroll={{ x: "max-content" }}
            size="small"
            pagination={{ pageSize: 8, showSizeChanger: false }}
          />
        ),
        tabLabel: "Table",
        icon: <TableOutlined />,
      },
    ];

    if (!chartImages || chartImages.length <= 0) {
      const {
        xAxisColumns,
        categoricalColumns,
        yAxisColumns,
        xAxisColumnValues,
        dateColumns,
      } = processData(response.data, response.columns);

      tabs.push({
        component: (
          <ErrorBoundary>
            <ChartContainer
              xAxisColumns={xAxisColumns}
              dateColumns={dateColumns}
              categoricalColumns={categoricalColumns}
              yAxisColumns={yAxisColumns}
              xAxisColumnValues={xAxisColumnValues}
              data={response.data}
              columns={response.columns}
              title={tableData.query}
              key="1"
              vizType={"Bar Chart"}
            ></ChartContainer>
          </ErrorBoundary>
        ),
        tabLabel: "Chart",
        icon: <BarChartOutlined />,
      });
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
    if (sql !== null) {
      // show the sql query
      tabs.push({
        component: (
          <ErrorBoundary>
            <>
              <p>The following query was generated:</p>
              <Editor
                className="language-sql table-code-ctr"
                value={sql}
                highlight={(code) => highlight(code, languages.sql, "sql")}
                onValueChange={(newVal) => updateCodeAndSql("sql", newVal)}
              />
            </>
          </ErrorBoundary>
        ),
        tabLabel: "SQL",
      });
    }

    if (codeStr !== null) {
      // show the codeStr query
      tabs.push({
        component: (
          <ErrorBoundary>
            <>
              <p>The following code was run:</p>
              <Editor
                className="language-python table-code-ctr"
                value={codeStr}
                highlight={(code) =>
                  highlight(code, languages.python, "python")
                }
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
          right: tableData.edited ? (
            <Button onClick={runAgain} className="edited-button" type="primary">
              {reRunning ? "Running..." : "Run again"}
            </Button>
          ) : (
            <></>
          ),
          left: tabBarLeftContent || <></>,
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
  }, [tableData, response]);

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
            data-table-id={tableId}
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
                              data-table-id=${tableId}>
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
                              data-table-id=${tableId}>
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

  function runAgain() {
    if (!socketManager.isConnected() || !socketManager) {
      message.error("Not connected to the servers.");
      return;
    }

    setReRunning(true);
    // else send it
    socketManager.send({
      run_again: true,
      table_id: tableId,
      data: tableData,
    });
  }

  return (
    <div className="table-chart-ctr" ref={tableChartRef}>
      {results}
      {reactiveVarJsx}
    </div>
  );
}
