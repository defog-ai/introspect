"use client";

import { useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  MessageManager,
  MessageManagerContext,
  MessageMonitor,
  Tabs,
} from "../agents-ui-components/lib/ui-components/lib/main";
import { QueryDataScaffolding } from "../agents-ui-components/lib/components/defog-components/QueryDataScaffolding";
import { twMerge } from "tailwind-merge";
import { AnalysisTreeManager } from "../agents-ui-components/lib/components/defog-components/agent/analysisTreeManager";
import { MetadataTabContent } from "./tab-content/MetadataTabContent";
import { AnalysisTabContent } from "./tab-content/AnalysisTabContent";
import { TabNullState } from "./tab-content/TabNullState";
import { getColumnDescriptionsForCsv } from "../agents-ui-components/lib/components/utils/utils";
import { PreviewDataTabContent } from "./tab-content/PreviewDataTabContent";
import {
  addParsedCsvToSqlite,
  initializeSQLite,
  validateTableName,
} from "../agents-ui-components/lib/components/utils/sqlite";

function TestDriveInner({
  token = null,
  apiEndpoint = null,
  csvFileKeyName = "Manufacturing",
  uploadedCsvPredefinedQuestions = ["Show me any 5 rows"],
  dbs,
}) {
  const ctr = useRef(null);
  const messageManager = useContext(MessageManagerContext);
  const conn = useRef(null);

  const [availableDbs, setAvailableDbs] = useState(dbs);

  const [selectedDbName, setSelectedDbName] = useState(null);

  const selectedDb = useMemo(() => {
    return availableDbs.find((d) => d.name === selectedDbName);
  }, [selectedDbName, availableDbs]);

  const selectedDbKeyName = useMemo(() => {
    return availableDbs.find((d) => d.name === selectedDbName)?.keyName;
  }, [selectedDbName, availableDbs]);

  const selectedDbMetadata = useMemo(() => {
    return availableDbs.find((d) => d.name === selectedDbName)?.metadata;
  }, [selectedDbName, availableDbs]);

  const selectedDbManager = useMemo(() => {
    return availableDbs.find((d) => d.name === selectedDbName)
      ?.analysisTreeManager;
  }, [selectedDbName, availableDbs]);

  const selectedDbPredefinedQuestions = useMemo(() => {
    return (
      availableDbs.find((d) => d.name === selectedDbName)
        ?.predefinedQuestions || []
    );
  }, [selectedDbName, availableDbs]);

  const [fileUploading, setFileUploading] = useState(false);

  const addCsvToDbListAndSqlite = async ({ file, columns, rows }) => {
    try {
      setFileUploading(true);
      const newDbName = file.name.split(".")[0];
      const sqliteTableName = validateTableName("csv_" + newDbName);

      let tableData, metadata;

      // also add to sqlite
      // once done uploading, also add it to sqlite db
      if (conn.current) {
        try {
          const { columnMetadata, fiveRowsAsArraysOfValues } =
            addParsedCsvToSqlite({
              conn: conn.current,
              tableName: sqliteTableName,
              rows: rows,
              columns,
            });

          messageManager.info(
            "CSV parsed, now generating descriptions for columns!"
          );

          // reformat to a format that PreviewDataTabContent expects
          // this is also the format we get back from integration/preview_table endpoint
          tableData = {
            [sqliteTableName]: {
              data: fiveRowsAsArraysOfValues,
              columns: columnMetadata.map((d) => d["dataIndex"]),
            },
          };

          // if any columns have hasMultipleTypes true, then we need to show a warning
          const multipleTypesColumns = columnMetadata.filter(
            (d) => d.hasMultipleTypes
          );

          if (multipleTypesColumns.length > 0) {
            messageManager.warning(
              `Columns ${multipleTypesColumns.map((d) => `'${d.title}'`).join(",")} have values of multiple data types. This might cause issues.`
            );
          }

          // re shape metadata into something defog servers expect
          // this will be stored internally and sent inr request bodies
          // we don't have column descriptions yet
          metadata = columnMetadata.map((d) => ({
            column_name: d.dataIndex,
            table_name: sqliteTableName,
            data_type: d.dataType,
          }));

          // get column descriptions.
          // we do this at the end to have *some metadata* in case we error out here
          const res = await getColumnDescriptionsForCsv({
            apiEndpoint: apiEndpoint,
            keyName: csvFileKeyName,
            metadata: metadata,
            tableName: sqliteTableName,
          });

          if (!res.success || res.error_message || !res.descriptions) {
            throw new Error(
              res.error_message ||
                "Failed to get column descriptions. Queries might be less precise."
            );
          }

          const columnDescriptions = res.descriptions;

          // if we got them successfully, merge them into the metadata object above
          metadata.forEach((m) => {
            const colDesc = columnDescriptions.find(
              (d) => d.column_name === m.column_name
            );

            if (colDesc) {
              m.column_description = colDesc.column_description;
            }
          });
        } catch (e) {
          console.log(e.stack);
          messageManager.error(e.message);
        }
      }

      // now add it to our db list
      setAvailableDbs((prev) => {
        const newDbs = [...prev];
        // if there's a temp one, replace it
        const tempDb = {
          name: newDbName,
          keyName: csvFileKeyName,
          isTemp: true,
          metadata: metadata || null,
          data: tableData,
          columns: columns,
          sqliteTableName,
          metadataFetchingError: false,
          predefinedQuestions: uploadedCsvPredefinedQuestions,
          analysisTreeManager: AnalysisTreeManager({}),
        };

        // const existingTempIdx = prev.findIndex((d) => d.isTemp);
        // if (existingTempIdx >= 0) {
        //   newDbs[existingTempIdx] = tempDb;
        // } else {
        newDbs.push(tempDb);
        // }

        return newDbs;
      });

      // set this to selected db
      setSelectedDbName(newDbName);
    } catch (e) {
      console.log(e.stack);
      messageManager.error(e.message);
    } finally {
      setFileUploading(false);
    }
  };

  const nullTab = useMemo(
    () => (
      <TabNullState
        availableDbs={availableDbs}
        onSelectDb={(selectedDbName) => setSelectedDbName(selectedDbName)}
        fileUploading={fileUploading}
        onParseCsv={addCsvToDbListAndSqlite}
      />
    ),
    [availableDbs, fileUploading]
  );

  const tabs = useMemo(() => {
    return [
      {
        name: "Analysis",
        headerClassNames: (selected, tab) =>
          twMerge(
            "bg-gray-100",
            tab.name === "Analysis"
              ? selected
                ? "bg-gray-600 text-white hover:bg-gray-600"
                : ""
              : ""
          ),
        content:
          !selectedDbManager || !selectedDbKeyName || !token || !apiEndpoint ? (
            nullTab
          ) : (
            <AnalysisTabContent
              selectedDbManager={selectedDbManager}
              selectedDbKeyName={selectedDbKeyName}
              selectedDbMetadata={selectedDbMetadata}
              predefinedQuestions={selectedDbPredefinedQuestions}
              token={token}
              apiEndpoint={apiEndpoint}
              config={{
                showAnalysis: false,
                showCode: false,
                allowDashboardAdd: false,
              }}
              isTemp={selectedDb.isTemp}
              sqliteConn={conn.current}
            />
          ),
      },
      {
        name: "View data structure",
        content: !selectedDb ? (
          nullTab
        ) : (
          <MetadataTabContent
            key={selectedDbKeyName}
            apiEndpoint={apiEndpoint}
            db={selectedDb}
            token={token}
            onGetMetadata={({ metadata, error }) => {
              setAvailableDbs((prev) => {
                const newDbs = [...prev];
                const idx = prev.findIndex((d) => d.name === selectedDbName);
                if (idx < 0) return newDbs;
                newDbs[idx] = Object.assign({}, newDbs[idx]);

                // if this is a temp db, then add a property called "sqlite_table_name" in metadata as the actual name
                if (selectedDb.isTemp) {
                  metadata.forEach((m) => {
                    m.sqlite_table_name = selectedDb.sqliteTableName;
                  });
                }

                newDbs[idx].metadata = metadata;
                // if there's an error, don't show the data
                if (error) {
                  newDbs[idx].metadataFetchingError = error;
                  newDbs[idx].data = {};
                  newDbs[idx].dataFetchingError = error || false;
                }

                return newDbs;
              });
            }}
          />
        ),
      },
      {
        name: "Preview data",
        content: !selectedDb ? (
          nullTab
        ) : (
          <PreviewDataTabContent
            key={selectedDbKeyName}
            apiEndpoint={apiEndpoint}
            db={selectedDb}
            token={token}
            onGetData={({ data }) => {
              setAvailableDbs((prev) => {
                const newDbs = [...prev];
                const idx = prev.findIndex((d) => d.name === selectedDbName);
                if (idx < 0) return newDbs;

                newDbs[idx] = Object.assign({}, newDbs[idx]);

                newDbs[idx].data = data;
                return newDbs;
              });
            }}
          />
        ),
      },
    ];
  }, [
    selectedDbManager,
    selectedDbKeyName,
    selectedDbName,
    selectedDb,
    nullTab,
  ]);

  useEffect(() => {
    (async () => {
      const _conn = await initializeSQLite();
      conn.current = _conn;

      window.sqlite = _conn;
    })();
  }, []);

  return (
    <QueryDataScaffolding
      defaultSelectedDb={selectedDbName}
      availableDbs={availableDbs.map((d) => d.name)}
      onDbChange={(selectedDbName) => setSelectedDbName(selectedDbName)}
      onParseCsv={addCsvToDbListAndSqlite}
      rootClassNames={(selectedDbName) => {
        return (
          "flex flex-col " +
          (!selectedDbName ? "items-center justify-center" : "")
        );
      }}
      fileUploading={fileUploading}
    >
      <Tabs
        disableSingleSelect={true}
        vertical={true}
        rootClassNames="grow h-[90%] w-full"
        contentClassNames="mt-2 sm:mt-0 bg-white grow overflow-hidden shadow-custom rounded-2xl sm:rounded-tl-none"
        defaultTabClassNames="pl-0 sm:mt-0 h-full"
        selectedTabHighlightClasses={(nm) =>
          nm === "Analysis" ? "bg-transparent" : ""
        }
        tabs={tabs}
      />
    </QueryDataScaffolding>
  );
}

/**
 * TestDrive component, renders the tabbed view with database selection + csv upload for agents.
 *
 * @param {Object} props
 * @param {String} props.token - The hashed password.
 * @param {String} props.apiEndpoint - The API endpoint to use for the requests
 * @param {Boolean} props.disableMessages - Whether to disable messages or not
 * @param {Array<{keyName: string, predefinedQuestions?: string[], name?: string}>} props.dbs - The list of databases to show in the dropdown. Each object should have a keyName and predefinedQuestions array.
 * @param {Array<string>} props.uploadedCsvPredefinedQuestions - The predefined questions for the uploaded CSVs
 *
 */
export function TestDrive({
  token = null,
  apiEndpoint = null,
  disableMessages = false,
  dbs = [],
  uploadedCsvPredefinedQuestions = ["Show me any 5 rows"],
}) {
  // use the simple db list
  // and add some extra props to them
  // including the analysis tree manager which helps us "remember" questions for each db
  const dbsWithManagers = useMemo(() => {
    return dbs.map((d) => ({
      ...d,
      isTemp: false,
      metadata: null,
      data: {},
      metadataFetchingError: false,
      analysisTreeManager: AnalysisTreeManager({}, d.keyName),
    }));
  }, [dbs]);

  return (
    <div className="w-full bg-gradient-to-br from-[#6E00A2]/10 to-[#FFA20D]/10 px-2 lg:px-0 py-8 my-8 h-screen flex items-center shadow-inner relative">
      <div className="w-full lg:w-10/12 min-h-96 h-[95%] overflow-y-hidden mx-auto">
        <MessageManagerContext.Provider value={MessageManager()}>
          <MessageMonitor
            rootClassNames={"absolute left-0 right-0"}
            disabled={disableMessages}
          />
          <TestDriveInner
            token={token}
            apiEndpoint={apiEndpoint}
            dbs={dbsWithManagers}
            uploadedCsvPredefinedQuestions={uploadedCsvPredefinedQuestions}
          />
        </MessageManagerContext.Provider>
      </div>
    </div>
  );
}
