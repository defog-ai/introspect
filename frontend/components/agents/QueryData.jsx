"use client";

import { useContext, useMemo, useRef, useState } from "react";
import {
  MessageManager,
  MessageManagerContext,
  MessageMonitor,
  Table,
  Tabs,
} from "../agents-ui-components/lib/ui-components/lib/main";
import { QueryDataScaffolding } from "../agents-ui-components/lib/components/defog-components/QueryDataScaffolding";
import { twMerge } from "tailwind-merge";
import { AnalysisVersionManager } from "../agents-ui-components/lib/components/defog-components/agent/analysisVersionManager";
import { MetadataTabContent } from "./tab-content/MetadataTabContent";
import { AnalysisTabContent } from "./tab-content/AnalysisTabContent";
import { TabNullState } from "./tab-content/TabNullState";
import { uploadFileToServer } from "../agents-ui-components/lib/components/utils/utils";
import { PreviewDataTabContent } from "./tab-content/PreviewDataTabContent";

const keyNames = process.env.NEXT_PUBLIC_API_KEY_NAMES || "";
// create an initial database list using the api key names
const dbs = keyNames.split(",").map((keyName) => ({
  name: keyName,
  keyName: keyName,
  isTemp: false,
  metadata: null,
  data: {},
  metadataFetchingError: false,
  analysisVersionManager: AnalysisVersionManager({}, keyName),
}));

// this is hte inner component. We wrap this component with the required context (Mostly just message manager)
// see the bottom of this file for the wrapped component
function QueryDataInner({
  devMode = false,
  token = null,
  apiEndpoint = null,
  predefinedQuestions = ["Show me any 5 rows"],
}) {
  const ctr = useRef(null);
  const messageManager = useContext(MessageManagerContext);

  const [availableDbs, setAvailableDbs] = useState(dbs);

  const [selectedDbName, setSelectedDbName] = useState(null);

  const selectedDb = useMemo(() => {
    return availableDbs.find((d) => d.name === selectedDbName);
  }, [selectedDbName, availableDbs]);

  const selectedDbKeyName = useMemo(() => {
    return availableDbs.find((d) => d.name === selectedDbName)?.keyName;
  }, [selectedDbName, availableDbs]);

  const selectedDbManager = useMemo(() => {
    return availableDbs.find((d) => d.name === selectedDbName)
      ?.analysisVersionManager;
  }, [selectedDbName, availableDbs]);

  const [fileUploading, setFileUploading] = useState(false);

  const addUploadedFileToDbList = ({ file, parsedData, columns, rows }) => {
    const newDbName = file.name.split(".")[0];

    setAvailableDbs((prev) => {
      const newDbs = [...prev];
      // if there's a temp one, replace it
      const tempDb = {
        name: newDbName,
        keyName: "Manufacturing",
        isTemp: true,
        metadata: null,
        data: {},
        columns: columns,
        metadataFetchingError: false,
        analysisVersionManager: AnalysisVersionManager({}),
      };

      const existingTempIdx = prev.findIndex((d) => d.isTemp);
      if (existingTempIdx >= 0) {
        newDbs[existingTempIdx] = tempDb;
      } else {
        newDbs.push(tempDb);
      }

      return newDbs;
    });

    // set this to selected db
    setSelectedDbName(newDbName);
  };

  const uploadFile = async ({ file, parsedData, rows, columns }) => {
    try {
      setFileUploading(true);
      // if file is greater than 10mb, don't upload it
      if (file.size > 10 * 1024 * 1024) {
        throw new Error("Max file size allowed is 10MB.");
      }

      await uploadFileToServer({
        token,
        apiEndpoint,
        keyName: "Manufacturing",
        file,
        parsedData,
        rows,
        columns,
        onFileUploadSuccess: addUploadedFileToDbList,
      });
    } catch (e) {
      messageManager.error(e);
      console.log(e.stack);
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
        onParseCsv={uploadFile}
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
              devMode={devMode}
              selectedDbManager={selectedDbManager}
              selectedDbKeyName={selectedDbKeyName}
              token={token}
              apiEndpoint={apiEndpoint}
              predefinedQuestions={predefinedQuestions}
              config={{
                showAnalysis: false,
                showCode: false,
                allowDashboardAdd: false,
              }}
              isTemp={selectedDb.isTemp}
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

  return (
    <QueryDataScaffolding
      defaultSelectedDb={selectedDbName}
      availableDbs={availableDbs.map((d) => d.name)}
      onDbChange={(selectedDbName) => setSelectedDbName(selectedDbName)}
      onParseCsv={uploadFile}
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

// wrap the above QueryDataInner component in the required context
export function QueryData({
  token = null,
  apiEndpoint = null,
  disableMessages = false,
  predefinedQuestions = ["Show me any 5 rows"],
  devMode = false,
}) {
  return (
    <div className="w-full pb-16 lg:pt-0 lg:pb-0 bg-gradient-to-br from-[#6E00A2]/10 to-[#FFA20D]/10 px-2 lg:px-0 grow flex items-center shadow-inner relative">
      <div className="w-full lg:w-10/12 min-h-96 h-[95%] overflow-y-hidden mx-auto">
        <MessageManagerContext.Provider value={MessageManager()}>
          <MessageMonitor
            rootClassNames={"absolute left-0 right-0"}
            disabled={disableMessages}
          />
          <QueryDataInner
            devMode={devMode}
            token={token}
            apiEndpoint={apiEndpoint}
            predefinedQuestions={predefinedQuestions}
          />
        </MessageManagerContext.Provider>
      </div>
    </div>
  );
}
