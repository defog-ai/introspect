import { useEffect, useMemo, useState } from "react";
import { twMerge } from "tailwind-merge";
import SingleSelect from "./SingleSelect";
import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/20/solid";

const allowedPageSizes = [5, 10, 20, 50, 100];

const defaultColumnHeaderRender = ({
  column,
  i,
  allColumns,
  toggleSort,
  sortOrder,
  sortColumn,
}) => {
  return (
    <th
      key={column.key}
      scope="col"
      className={twMerge(
        i === 0 ? "pl-4" : "px-3",
        "py-3.5 text-left text-sm font-semibold text-gray-900",
        i === allColumns.length - 1 ? "pr-4 sm:pr-6 lg:pr-8" : ""
      )}
    >
      <div className="flex flex-row items-center">
        <p className="grow">{column.title}</p>
        <div className="sorter-arrows ml-5 flex flex-col items-center w-4 overflow-hidden">
          <button className="h-3">
            <div
              onClick={() => {
                toggleSort(column, "asc");
              }}
              className={twMerge(
                "arrow-up cursor-pointer",
                "border-b-[5px] border-b-gray-300 hover:border-b-gray-500",
                sortOrder === "asc" && sortColumn.title === column.title
                  ? "border-b-gray-500"
                  : ""
              )}
            />
          </button>
          <button className="h-3">
            <div
              onClick={() => {
                toggleSort(column, "desc");
              }}
              className={twMerge(
                "arrow-down cursor-pointer",
                "border-t-[5px] border-t-gray-300 hover:border-t-gray-500",
                sortOrder === "desc" && sortColumn.title === column.title
                  ? "border-t-gray-500"
                  : ""
              )}
            />
          </button>
        </div>
      </div>
    </th>
  );
};

const defaultRowCellRender = ({
  cellValue,
  i,
  row,
  dataIndex,
  column,
  dataIndexes,
  allColumns,
  dataIndexToColumnMap,
}) => (
  <td
    key={row.key + "-" + dataIndex}
    className={twMerge(
      i === 0 ? "pl-4" : "px-3",
      "py-4 text-sm text-gray-500",
      i === dataIndexes.length - 1 ? "pr-4 sm:pr-6 lg:pr-8" : ""
    )}
  >
    {cellValue}
  </td>
);

const defaultSorter = (a, b) => {
  return String(a).localeCompare(String(b));
};

export default function Table({
  columns,
  rows,
  rootClassName = "",
  pagination = { defaultPageSize: 10, showSizeChanger: true },
  skipColumns = [],
  rowCellRender = (...args) => null,
}) {
  // name of the property in the rows objects where each column's data is stored
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(pagination.defaultPageSize);
  const columnsToDisplay = useMemo(
    () =>
      columns
        .filter((column) => !skipColumns.includes(column.dataIndex))
        .map((d) => ({
          ...d,
          cellRender: d.cellRender || defaultColumnHeaderRender,
        })),
    [columns, skipColumns]
  );

  const [sortColumn, setSortColumn] = useState(null);
  const [sortOrder, setSortOrder] = useState(null);
  const [sortedRows, setSortedRows] = useState(rows);

  const dataIndexes = columnsToDisplay.map((d) => d.dataIndex);
  const dataIndexToColumnMap = columnsToDisplay.reduce((acc, column) => {
    acc[column.dataIndex] = column;
    return acc;
  }, {});

  const maxPage = Math.ceil(rows.length / pageSize);

  function toggleSort(newColumn, newOrder) {
    // if everything the same, set null
    if (sortColumn?.title === newColumn?.title && sortOrder === newOrder) {
      setSortColumn(null);
      setSortOrder(null);
    } else {
      setSortColumn(newColumn);
      setSortOrder(newOrder);
    }
  }

  useEffect(() => {
    if (sortColumn && sortOrder) {
      // each column has a sorter function defined
      const sorter = sortColumn.sorter || defaultSorter;
      const sortedRows = rows.slice().sort((a, b) => {
        return sortOrder === "asc" ? sorter(a, b) : sorter(b, a);
      });
      setSortedRows(sortedRows);
    } else {
      setSortedRows(rows);
    }
  }, [sortColumn, rows, sortOrder]);

  return (
    <div className={twMerge("overflow-auto", rootClassName)}>
      <div className="overflow-auto max-w-6xl">
        <div className="py-2">
          <table className="divide-y w-full divide-gray-300">
            <thead className="bg-gray-50">
              <tr>
                {columnsToDisplay.map((column, i) => {
                  return column.cellRender({
                    column,
                    i,
                    allColumns: columnsToDisplay,
                    toggleSort,
                    sortOrder,
                    sortColumn,
                  });
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {sortedRows
                .slice((currentPage - 1) * pageSize, currentPage * pageSize)
                .map((row) => (
                  <tr key={row.key}>
                    {dataIndexes.map(
                      (dataIndex, i) =>
                        rowCellRender({
                          cellValue: row[dataIndex],
                          i,
                          row,
                          dataIndex,
                          column: dataIndexToColumnMap[dataIndex],
                          dataIndexes,
                          allColumns: columnsToDisplay,
                          dataIndexToColumnMap,
                        }) ||
                        defaultRowCellRender({
                          cellValue: row[dataIndex],
                          i,
                          row,
                          dataIndex,
                          column: dataIndexToColumnMap[dataIndex],
                          dataIndexes,
                          allColumns: columnsToDisplay,
                          dataIndexToColumnMap,
                        })
                    )}
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
      {rows.length > allowedPageSizes[0] && (
        <div className="pl-4 pager mt-3 text-center bg-white">
          <div className="w-full flex flex-row justify-end items-center">
            <div className="flex flex-row w-50 items-center">
              <div className="text-gray-600">
                Page
                <span className="mx-1 font-semibold">{currentPage}</span>/
                <span className="mx-1 font-semibold">{maxPage}</span>
              </div>
              <ChevronLeftIcon
                className={twMerge(
                  "w-5 cursor-not-allowed",
                  currentPage === 1
                    ? "text-gray-300"
                    : "hover:text-blue-500 cursor-pointer"
                )}
                onClick={() => {
                  setCurrentPage(currentPage - 1 < 1 ? 1 : currentPage - 1);
                }}
              />
              <ChevronRightIcon
                className={twMerge(
                  "w-5 cursor-pointer",
                  currentPage === maxPage
                    ? "text-gray-300 cursor-not-allowed"
                    : "hover:text-blue-500 cursor-pointer"
                )}
                onClick={() => {
                  setCurrentPage(
                    currentPage + 1 > maxPage ? maxPage : currentPage + 1
                  );
                }}
              />
            </div>
            <div className="w-full flex">
              <SingleSelect
                rootClassName="w-24"
                options={allowedPageSizes.map((d) => ({ value: d, label: d }))}
                defaultValue={pageSize}
                onChange={(val) => setPageSize(val || 10)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
