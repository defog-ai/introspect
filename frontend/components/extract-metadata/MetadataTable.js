import { useState, useEffect, useContext } from "react";
import {
  // Remove Alert, Table, Spin
  Edit,
  Save,
  Upload,
  Download,
} from "lucide-react";
import setupBaseUrl from "$utils/setupBaseUrl";
import {
  MessageManagerContext,
  MultiSelect,
  Table as DefogTable,
  SpinningLoader,
} from "@defogdotai/agents-ui-components/core-ui";

const MetadataTable = ({
  token,
  apiKeyName,
  tablesData,
  initialMetadata,
  setColumnDescriptionCheck,
}) => {
  // all tables from the database
  const [tables, setTables] = useState([]);
  // tables indexed for defog
  const [selectedTablesForIndexing, setSelectedTablesForIndexing] = useState([]);
  const [metadata, setMetadata] = useState(initialMetadata);
  const [filteredMetadata, setFilteredMetadata] = useState(initialMetadata);

  // key (table_name_column_name): value (boolean) to toggle editing
  const [editingKeys, setEditingKeys] = useState({});

  const [loading, setLoading] = useState(false);
  const [desc, setDesc] = useState({});
  const [filter, setFilter] = useState([]); // list of table names to filter
  const [pageSize, setPageSize] = useState(10);

  const hasNonEmptyDescriptionFunction = (metadataArr) => {
    return metadataArr.some(
      (item) =>
        item.column_description && item.column_description.trim() !== ""
    );
  };

  const message = useContext(MessageManagerContext);

  useEffect(() => {
    if (tablesData) {
      setTables(tablesData.tables);
      setSelectedTablesForIndexing(tablesData.indexed_tables);
    }
  }, [tablesData]);

  useEffect(() => {
    setMetadata(initialMetadata);
    setFilteredMetadata(initialMetadata);
  }, [initialMetadata]);

  useEffect(() => {
    setFilteredMetadata(metadata);
  }, [metadata]);

  const fetchMetadata = async () => {
    setLoading(true);
    const res = await fetch(setupBaseUrl("http", `integration/get_metadata`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token,
        db_name: apiKeyName,
      }),
    });
    if (res.status === 401) {
      message.error("Your credentials are incorrect. Please log in again.");
      setLoading(false);
      return;
    }
    const data = await res.json();
    setLoading(false);
    if (!data.error) {
      setMetadata(data.metadata || []);
    } else {
      setMetadata([]);
    }
  };

  const updateMetadata = async () => {
    try {
      setLoading(true);
      const res = await fetch(
        setupBaseUrl("http", `integration/update_metadata`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            metadata,
            token,
            db_name: apiKeyName,
          }),
        }
      );
      const data = await res.json();
      setLoading(false);
      if (data.error) {
        message.error(data.error || "Error updating metadata", 10);
      } else {
        if (data.suggested_joins) {
          document.getElementById("allowed-joins").value = data.suggested_joins;
        }
        if (data.detail) {
          message.error(data.detail, 3);
        } else {
          message.success("Metadata updated successfully!");
          setColumnDescriptionCheck(hasNonEmptyDescriptionFunction(metadata));
        }
      }
    } catch (error) {
      console.error("Error saving data:", error);
      message.error("Error saving data");
      setLoading(false);
    }
  };

  const toggleEdit = (key) => {
    setEditingKeys((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleInputChange = (e, key) => {
    const newValue = e.target.value;
    const updatedMetadata = metadata.map((item) => {
      const itemKey = `${item.table_name}_${item.column_name}`;
      if (itemKey === key) {
        return { ...item, column_description: newValue };
      }
      return item;
    });
    setMetadata(updatedMetadata);

    // Reapply the filter if there's an active filter
    if (filter.length > 0) {
      const filtered = updatedMetadata.filter((item) =>
        filter.some((f) => item.table_name.includes(f))
      );
      setFilteredMetadata(filtered);
    } else {
      setFilteredMetadata(updatedMetadata);
    }
  };

  const reIndexTables = async () => {
    console.log("Received tables: ", selectedTablesForIndexing);
    setLoading(true);
    try {
      message.info(
        "Extracting metadata from selected tables. This can take up to 5 minutes. Please be patient."
      );
      const res = await fetch(
        setupBaseUrl("http", `integration/generate_metadata`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tables: selectedTablesForIndexing,
            token,
            db_name: apiKeyName,
          }),
        }
      );
      const data = await res.json();
      setLoading(false);
      if (data.error) {
        message.error("Error fetching metadata");
      } else {
        setMetadata(data.metadata || []);
        setFilteredMetadata(data.metadata || []);
      }
    } catch (e) {
      console.log(e);
      setLoading(false);
      message.error(
        "Error fetching metadata - please look at your docker logs for more information."
      );
    }
  };

  const handleFilterChange = (value) => {
    setFilter(value);
    if (value.length > 0) {
      setFilteredMetadata(
        metadata.filter((item) =>
          value.some((v) => item.table_name.includes(v))
        )
      );
    } else {
      setFilteredMetadata(metadata);
    }
  };

  // to remove duplicate table names
  const uniqueTableNames = [
    ...new Set(metadata.map((item) => item.table_name)),
  ].filter(Boolean);

  // We'll keep your original columns array. We'll replicate the <select> header, etc.
  const columns = [
    {
      title: "Table Name",
      dataIndex: "table_name",
      key: "table_name",
      width: "20%",
      align: "left",
      render: (text) => <span className="font-bold">{text}</span>,
    },
    {
      title: "Column Name",
      dataIndex: "column_name",
      key: "column_name",
      width: "20%",
      align: "left",
      render: (text) => <span className="font-semibold">{text}</span>,
    },
    {
      title: "Data Type",
      dataIndex: "data_type",
      key: "data_type",
      width: "20%",
      align: "left",
      render: (text) => <span className="font-mono">{text}</span>,
    },
    {
      title: "Description",
      dataIndex: "column_description",
      key: "column_description",
      width: "35%",
      align: "left",
      render: (text, record) => {
        const key = `${record.table_name}_${record.column_name}`;
        if (editingKeys[key]) {
          return (
            <textarea
              defaultValue={text}
              onChange={(e) => handleInputChange(e, key)}
              rows={2}
              className="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-dark-bg-secondary dark:border-dark-border dark:text-dark-text-primary"
            />
          );
        }
        return <span className="italic">{text}</span>;
      },
    },
    {
      key: "action",
      width: "5%",
      align: "right", // Keep actions right-aligned for better UX
      render: (text, record) => {
        const key = `${record.table_name}_${record.column_name}`;
        return editingKeys[key] ? (
          <Save onClick={() => toggleEdit(key)} />
        ) : (
          <Edit onClick={() => toggleEdit(key)} />
        );
      },
    },
  ];

  const tableData = filteredMetadata.map((item) => ({
    key: `${item.table_name}_${item.column_name}`,
    ...item,
  }));

  const addAllTables = () => {
    setSelectedTablesForIndexing(tables);
  };

  const clearAllTables = () => {
    setSelectedTablesForIndexing([]);
  };

  const downloadMetadata = async () => {
    // download metadata as CSV
    const response = await fetch(
      setupBaseUrl("http", `integration/get_metadata`),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          db_name: apiKeyName,
          format: "csv",
        }),
      }
    );
    const resp = await response.json();
    if (resp.error) {
      message.error(resp.error);
    } else {
      const url = window.URL.createObjectURL(new Blob([resp.metadata]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "metadata.csv");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const uploadMetadata = async () => {
    // upload a file containing metadata
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".csv";

    fileInput.onchange = async (e) => {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = async (ev) => {
        const metadataCsv = ev.target.result;
        const response = await fetch(
          setupBaseUrl("http", `integration/upload_metadata`),
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              token,
              db_name: apiKeyName,
              metadata_csv: metadataCsv,
            }),
          }
        );
        if (!response.ok) {
          const resp = await response.json();
          message.error(resp.error || "Error uploading metadata", 10);
          return;
        } else {
          message.success("Metadata uploaded successfully! Reloading...");
          await fetchMetadata();
        }
      };
      reader.readAsText(file);
    };

    setLoading(true);
    fileInput.click();
    setLoading(false);
  };

  console.log(tables);
  console.log(selectedTablesForIndexing);

  // We'll replicate the old "Alert" with a Tailwind info box
  const InfoAlert = () => (
    <div className="mb-4 px-3 py-2 rounded border border-blue-300 bg-blue-50 text-blue-800">
      <span className="font-semibold pr-1">Info:</span>{" "}
      This table is a preview for your changes. Please hit 'Save Changes' to
      update metadata on the defog server, or upload your metadata as a CSV
    </div>
  );


  if (loading) {
    return (
      <div className="relative dark:bg-dark-bg-primary space-y-4">
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/70 dark:bg-gray-900/70 backdrop-blur-[1px]">
          <SpinningLoader classNames="text-blue-500 h-6 w-6" />
          <span className="ml-2 text-gray-600 dark:text-gray-300">
            Fetching metadata...
          </span>
        </div>
        {/* We'll still render your layout behind the overlay, or you can return null */}
        <div className="pointer-events-none">
          {/* Below is your normal layout behind the overlay */}
          <div className="space-y-2 p-4">
            <div className="text-lg font-medium text-center dark:text-dark-text-primary">
              View and Update Metadata
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 dark:bg-dark-bg-primary">
      <div className="space-y-2">
        <div className="text-xl font-medium text-center dark:text-dark-text-primary mt-2">
          View and Update Metadata
        </div>
        
        <div className="w-full dark:bg-dark-bg-secondary">
          <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-primary mb-1">
            Select tables
          </label>
          {tables && (
            <MultiSelect
              options={tables.map((table) => ({ label: table, value: table }))}
              value={selectedTablesForIndexing || []}
              onChange={(value) => setSelectedTablesForIndexing(value)}
              rootClassNames="w-full max-w-[1000px]"
            />
          )}
          <div className="flex justify-between mt-2">
            <button
              type="button"
              className="mr-4 px-4 py-1 bg-gray-100 border border-gray-300 rounded-md shadow-sm hover:bg-gray-200 transition-colors duration-200 dark:bg-dark-bg-secondary dark:border-dark-border"
              onClick={addAllTables}
            >
              Add All ➕
            </button>
            <button
              type="button"
              className="px-4 py-1 bg-gray-100 border border-gray-300 rounded-md shadow-sm hover:bg-gray-200 transition-colors duration-200 dark:bg-dark-bg-secondary dark:border-dark-border"
              onClick={clearAllTables}
            >
              Clear All ❌
            </button>
          </div>
        </div>

        <button
          type="submit"
          className="w-64 bg-white border border-gray-300 text-blue-500 hover:bg-blue-500 hover:text-white self-center dark:bg-dark-bg-secondary dark:border-dark-border dark:text-dark-text-primary dark:hover:bg-dark-hover px-4 py-2 rounded-md"
          onClick={() => reIndexTables({ tables: selectedTablesForIndexing })}
          disabled={loading}
        >
          Extract Table Metadata
        </button>
      </div>

      {/* Action buttons */}
      <div className="flex justify-center my-4 gap-4">
        <button
          className="rounded bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:bg-dark-bg-secondary dark:text-dark-text-primary dark:border-dark-border dark:hover:bg-dark-hover disabled:opacity-50"
          disabled={loading}
          onClick={updateMetadata}
        >
          Save Changes
        </button>

        <button
          className="bg-white text-gray-700 font-semibold py-2 px-4 border border-gray-300 rounded shadow-sm hover:bg-gray-50 mr-2 flex items-center gap-2"
          disabled={loading}
          onClick={downloadMetadata}
        >
          <span>Download</span> <Download className="h-4 w-4" />
        </button>

        <button
          className="bg-white text-gray-700 font-semibold py-2 px-4 border border-gray-300 rounded shadow-sm hover:bg-gray-50 flex items-center gap-2"
          disabled={loading}
          onClick={uploadMetadata}
        >
          <span>Upload</span> <Upload className="h-4 w-4" />
        </button>
      </div>

      {/* Replicating the old Alert with a Tailwind info box */}
      <InfoAlert />

      {/* Table name filter moved here, right above the table */}
      <div className="w-full mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-primary mb-1">
          Filter by Table Name
        </label>
        <select
          multiple
          value={filter}
          onChange={(e) =>
            handleFilterChange(
              Array.from(e.target.selectedOptions, (option) => option.value)
            )
          }
          className="w-full p-2 text-xs border border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-dark-bg-secondary dark:border-dark-border dark:text-dark-text-primary"
        >
          {uniqueTableNames.map((table) => (
            <option key={table} value={table}>
              {table}
            </option>
          ))}
        </select>
      </div>

      {/* Defog Table. We'll replicate pagination, scroll, onChange, etc. */}
      <div className="max-h-[1200px] overflow-auto dark:bg-dark-bg-secondary">
        <DefogTable
          columns={columns}
          rows={tableData}
          // We'll store pageSize in our own state. Defog uses "defaultPageSize" and "showSizeChanger"
          pagination={{
            defaultPageSize: pageSize,
            showSizeChanger: true,
          }}
          paginationPosition="bottom"
          // We also replicate onChange by hooking into onPageSizeChange
          onPageSizeChange={(newSize) => {
            setPageSize(newSize);
          }}
          rowCellRender={({ cellValue, row, dataIndex, column }) => {
            // If column.render is a function, call it
            if (typeof column.render === "function") {
              return (
                <td
                  key={`${row.key}-${dataIndex}`}
                  className="px-3 py-2 align-top text-sm text-gray-700 dark:text-gray-200"
                >
                  {column.render(cellValue, row)}
                </td>
              );
            }
            // Fallback
            return (
              <td
                key={`${row.key}-${dataIndex}`}
                className="px-3 py-2 align-top text-sm text-gray-700 dark:text-gray-200"
              >
                {cellValue}
              </td>
            );
          }}
        />
      </div>
    </div>
  );
};

export default MetadataTable;
