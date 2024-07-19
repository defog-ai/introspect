import { useContext, useEffect, useState } from "react";
import {
  MessageManagerContext,
  MultiSelect,
  SpinningLoader,
  Table,
} from "../../agents-ui-components/lib/ui-components/lib/main";
import { twMerge } from "tailwind-merge";
import ErrorBoundary from "$components/layout/ErrorBoundary";

export function MetadataTabContent({
  apiEndpoint = null,
  db = null,
  token = null,
  onGetMetadata = (...args) => {},
}) {
  const messageManager = useContext(MessageManagerContext);
  let { keyName, metadata, isTemp } = db || {};

  useEffect(() => {
    if (!db) return;

    const hasMetadata = db.metadata ? true : false;
    async function getMetadata() {
      if (!apiEndpoint || !keyName || !token) {
        messageManager.error("Failed to get metadata");
        return;
      }
      let fetchedMetadata;
      try {
        const resp = await fetch(`${apiEndpoint}/integration/get_metadata`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            token: token,
            key_name: keyName,
            temp: isTemp,
          }),
        });

        fetchedMetadata = await resp.json();
        if (fetchedMetadata.error) {
          throw new Error(fetchedMetadata.error);
        }
      } catch (e) {
        console.log(e);
        fetchedMetadata = { error: "Error fetching metadata." };
      } finally {
        onGetMetadata(fetchedMetadata);
      }
    }

    if (!hasMetadata && !db.metadataFetchingError) {
      getMetadata();
    }
  }, [db]);

  const tables =
    Array.isArray(metadata) && !db.metadataFetchingError
      ? Array.from(new Set(metadata.map((col) => col.table_name)))
      : [];

  const columns =
    Array.isArray(metadata) && !db.metadataFetchingError
      ? [
          { dataIndex: "table_name", title: "table_name", key: "table_name" },
          {
            dataIndex: "column_name",
            title: "column_name",
            key: "column_name",
          },
          {
            dataIndex: "column_description",
            title: "column_description",
            key: "column_description",
          },
          { dataIndex: "data_type", title: "data_type", key: "data_type" },
        ]
      : [];

  const [selectedTables, setSelectedTables] = useState(tables);

  const tableRows =
    Array.isArray(metadata) && !db.metadataFetchingError
      ? metadata.filter((d) => {
          return selectedTables.length === 0
            ? true
            : selectedTables.includes(d.table_name);
        })
      : [];

  return (
    <ErrorBoundary>
      <div
        className={twMerge(
          "p-2 w-full h-full flex ",
          Array.isArray(metadata) && !db.metadataFetchingError
            ? "flex-col items-start justify-start"
            : "items-center justify-center"
        )}
      >
        {Array.isArray(metadata) && !db.metadataFetchingError ? (
          <>
            <div className="flex flex-col justify-center w-full">
              <div className="py-2 border-b bg-white sticky top-2 mb-3 z-[20]">
                <MultiSelect
                  rootClassNames="max-w-full"
                  placeholder="Filter tables"
                  value={[]}
                  options={tables.map((d) => ({ label: d, value: d }))}
                  onChange={(tableNames) => {
                    setSelectedTables(tableNames);
                  }}
                  allowCreateNewOption={false}
                />
              </div>

              <Table
                pagination={{
                  defaultPageSize: 5,
                }}
                paginationPosition="top"
                rootClassNames="rounded-md max-w-full"
                columns={columns}
                rows={tableRows}
                columnHeaderClassNames="py-2"
              />
            </div>
          </>
        ) : (
          <div className="text-center">
            {!db.metadataFetchingError ? (
              <>
                <div>Fetching</div>{" "}
                <SpinningLoader classNames="w-4 h-4 text-gray-500" />
              </>
            ) : (
              db.metadataFetchingError
            )}
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}
