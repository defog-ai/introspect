import { useContext, useEffect, useMemo, useState } from "react";
import {
  MessageManagerContext,
  MultiSelect,
  SingleSelect,
  SpinningLoader,
  Table,
} from "../../agents-ui-components/lib/ui-components/lib/main";
import { twMerge } from "tailwind-merge";
import ErrorBoundary from "$components/layout/ErrorBoundary";

export function PreviewDataTabContent({
  apiEndpoint = null,
  db = null,
  token = null,
  onGetData = (...args) => {},
}) {
  const messageManager = useContext(MessageManagerContext);
  let { keyName, isTemp } = db || {};

  useEffect(() => {
    // we need ot have metadata to fetch data
    if (!db || !db.metadata || db.metadataFetchingError) return;

    async function getData() {
      const tables =
        Array.isArray(db.metadata) && !db.metadataFetchingError
          ? Array.from(new Set(db.metadata.map((col) => col.table_name)))
          : [];

      // fetch for each table
      const data = {};
      let error;

      tables.forEach(async (tableName, i) => {
        data[tableName] = {
          data: [],
          columns: [],
          error: false,
        };

        let fetchedData;

        try {
          if (!apiEndpoint || !keyName || !token) {
            throw new Error("Failed to get data");
          }

          const resp = await fetch(`${apiEndpoint}/integration/preview_table`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              token: token,
              key_name: keyName,
              temp: isTemp,
              table_name: tableName,
            }),
          });

          fetchedData = await resp.json();

          if (fetchedData.error) {
            throw new Error(fetchedData.error);
          }

          fetchedData.tableName = tableName;
        } catch (e) {
          console.log(e);
          error = e;
          fetchedData = { error: "Failed to fetch data." };
        } finally {
          data[tableName] = {
            ...data[tableName],
            data: fetchedData.data.slice(),
            columns: fetchedData.columns.slice(),
          };

          if (i === tables.length - 1) {
            onGetData({ data, error });
          }
        }
      });
    }

    const hasData =
      !db.dataFetchingError &&
      !db.metadataFetchingError &&
      db.metadata &&
      db.data &&
      Object.keys(db.data).length > 0;

    if (!hasData) {
      getData();
    }
  }, [db]);

  const hasData =
    !db.dataFetchingError &&
    !db.metadataFetchingError &&
    db.metadata &&
    db.data &&
    Object.keys(db.data).length > 0;

  const hasError = db.dataFetchingError || db.metadataFetchingError;

  const tables = useMemo(() => {
    return Array.isArray(db.metadata) && !db.metadataFetchingError
      ? Array.from(new Set(db.metadata.map((col) => col.table_name)))
      : [];
  }, [db]);

  const [selectedTableIdx, setSelectedTableIdx] = useState(0);

  const selectedTableColumns = useMemo(() => {
    return (db?.data?.[tables?.[selectedTableIdx]]?.columns || []).map((d) => ({
      dataIndex: d,
      key: d,
      title: d,
    }));
  }, [selectedTableIdx, db]);

  const selectedTableData = useMemo(() => {
    const rows = db?.data?.[tables?.[selectedTableIdx]]?.data || [];
    return rows.map((rowArr) => {
      const rowObj = {};
      selectedTableColumns.forEach((col, idx) => {
        rowObj[col.dataIndex] = rowArr[idx];
      });

      return rowObj;
    });
  }, [selectedTableIdx, db]);

  return (
    <ErrorBoundary>
      <div
        className={twMerge(
          "p-2 w-full h-full flex ",
          hasData ? "" : "items-center justify-center"
        )}
      >
        {hasData ? (
          <>
            <div className="flex flex-col py-2 relative w-full">
              {/* table selector */}
              <div className="flex flex-row items-center mb-4 sticky top-4 z-[20] bg-white p-2 border-b">
                <SingleSelect
                  value={selectedTableIdx}
                  onChange={(val) => setSelectedTableIdx(val)}
                  options={tables.map((d, i) => ({
                    value: i,
                    label: d,
                  }))}
                  allowClear={false}
                  label="Select table"
                  allowCreateNewOption={false}
                />
              </div>
              <div className="max-w-full overflow-scroll">
                <Table
                  pagination={{
                    defaultPageSize: 5,
                  }}
                  paginationPosition="top"
                  rootClassNames="rounded-md max-w-full"
                  columns={selectedTableColumns}
                  rows={selectedTableData}
                  columnHeaderClassNames="py-2"
                />
              </div>
            </div>
          </>
        ) : !hasError ? (
          <>
            <div className="text-center">
              <div>Fetching</div>{" "}
              <SpinningLoader classNames="w-4 h-4 text-gray-500" />
            </div>
          </>
        ) : (
          <div className="text-center">
            {db.dataFetchingError || db.metadataFetchingError}
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}
