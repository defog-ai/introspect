import {
  useState,
  useEffect,
  useContext,
  useRef,
  useMemo,
  useCallback,
} from "react";
import {
  // Remove Alert, Table, Spin
  Upload,
  Download,
  InfoIcon,
  TextSearch,
} from "lucide-react";
import setupBaseUrl from "$utils/setupBaseUrl";
import {
  MessageManagerContext,
  MultiSelect,
  Table as DefogTable,
  SpinningLoader,
  Button,
  TextArea,
} from "@defogdotai/agents-ui-components/core-ui";
import { DbInfo } from "$utils/utils";
import debounce from "lodash.debounce";

const MetadataTable = ({
  token,
  dbInfo,
  onUpdate = () => {},
}: {
  token: string;
  dbInfo: DbInfo;
  onUpdate: (dbName: string, newDbInfo: DbInfo) => void;
}) => {
  // all tables from the database
  const [tables, setTables] = useState(dbInfo.tables || []);
  // tables indexed for defog
  const [selectedTablesForIndexing, setSelectedTablesForIndexing] = useState(
    dbInfo.selected_tables || []
  );
  const [metadata, setMetadata] = useState(dbInfo?.metadata || []);

  // key (table_name_column_name): value (boolean) to toggle editing
  const [editingKeys, setEditingKeys] = useState({});

  const [loading, setLoading] = useState(false);

  const dbName = dbInfo.db_name;

  const message = useContext(MessageManagerContext);

  useEffect(() => {
    setMetadata(dbInfo?.metadata || []);
    setTables(dbInfo?.tables || []);
    setSelectedTablesForIndexing(dbInfo?.selected_tables || []);
  }, [dbInfo]);

  const fetchMetadata = async () => {
    setLoading(true);
    const res = await fetch(setupBaseUrl("http", `integration/get_metadata`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token,
        db_name: dbName,
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

  const updateMetadata = useCallback(
    debounce(async (latestMetadata) => {
      try {
        const res = await fetch(
          setupBaseUrl("http", `integration/update_metadata`),
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              metadata: latestMetadata,
              token,
              db_name: dbName,
            }),
          }
        );

        const data = await res.json();
        if (data.error) {
          message.error(data.error || "Error updating metadata", 10);
        } else {
          message.success("Metadata updated successfully!");
        }
      } catch (error) {
        console.error("Error saving data:", error);
        message.error("Error saving data");
      }
    }, 500),
    [dbName]
  );

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
    updateMetadata(updatedMetadata);
  };

  const multiSelectOptions = useMemo(
    () => [
      {
        label: "All tables",
        value: "all",
      },
      {
        label: "Clear all",
        value: "clear",
      },
      ...dbInfo.tables.map((table) => ({ label: table, value: table })),
    ],
    [dbInfo]
  );

  const reIndexTables = async () => {
    console.log("Received tables: ", selectedTablesForIndexing);
    setLoading(true);
    try {
      message.info("Scanning selected tables.");
      const res = await fetch(
        setupBaseUrl("http", `integration/generate_metadata`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tables: selectedTablesForIndexing,
            token,
            db_name: dbName,
          }),
        }
      );

      if (!res.ok) {
        throw Error("Could not extract metadata from tables");
      }

      const newDbInfo = await res.json();

      onUpdate(dbName, newDbInfo);
    } catch (e) {
      console.log(e);
      message.error(
        "Error fetching metadata - please look at your docker logs for more information."
      );
    } finally {
      setLoading(false);
    }
  };

  // We'll keep your original columns array. We'll replicate the <select> header, etc.
  const columns = [
    {
      title: "Table Name",
      dataIndex: "table_name",
      key: "table_name",
      width: "20%",
      align: "left",
      render: (text) => <span className="p-2 font-bold">{text}</span>,
    },
    {
      title: "Column Name",
      dataIndex: "column_name",
      key: "column_name",
      width: "20%",
      align: "left",
      render: (text) => <span className="p-2 font-semibold">{text}</span>,
    },
    {
      title: "Data Type",
      dataIndex: "data_type",
      key: "data_type",
      width: "20%",
      align: "left",
      render: (text) => <span className="p-2 font-mono">{text}</span>,
    },
    {
      title: "Description (Edit to update)",
      dataIndex: "column_description",
      key: "column_description",
      width: "35%",
      align: "left",
      render: (text, record) => {
        const key = `${record.table_name}_${record.column_name}`;
        return (
          <TextArea
            defaultValue={text}
            autoResize={true}
            defaultRows={1}
            onChange={(e) => handleInputChange(e, key)}
            textAreaClassNames="resize-none outline-transparent shadow-none"
            // className="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-dark-bg-secondary dark:border-dark-border dark:text-dark-text-primary"
          />
        );
      },
    },
  ];

  const tableData = metadata.map((item) => ({
    key: `${item.table_name}_${item.column_name}`,
    ...item,
  }));

  const downloadMetadata = async () => {
    // download metadata as CSV
    const response = await fetch(
      setupBaseUrl("http", `integration/get_metadata`),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          db_name: dbName,
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
      // @ts-ignore
      const file = e.currentTarget.files[0];
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
              db_name: dbName,
              metadata_csv: metadataCsv,
            }),
          }
        );
        if (!response.ok) {
          message.error("Error uploading metadata");
          return;
        } else {
          const newDbInfo = await response.json();

          onUpdate(dbName, newDbInfo);

          message.success("Metadata uploaded successfully!");
        }
      };
      reader.readAsText(file);
    };

    setLoading(true);
    fileInput.click();
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="relative space-y-4">
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
    <div className="space-y-10">
      <div className="flex flex-row items-center text-blue-500 rounded-lg dark:text-blue-700 gap-2 text-sm">
        <InfoIcon />
        Extracting table and column metadata helps our AI generate more accurate
        SQL queries.
      </div>
      <div className="flex flex-row items-start gap-2 w-full border-b pb-10">
        {tables && (
          <MultiSelect
            placeholder="Select tables for metadata extraction. Leave empty to process all tables."
            options={multiSelectOptions}
            value={selectedTablesForIndexing}
            allowCreateNewOption={false}
            onChange={(value) => {
              if (value.indexOf("all") > -1) {
                setSelectedTablesForIndexing(tables);
                return;
              }

              if (value.indexOf("clear") > -1) {
                setSelectedTablesForIndexing([]);
                return;
              }

              setSelectedTablesForIndexing(value);
            }}
            rootClassNames="max-w-full grow"
          />
        )}
        <Button
          onClick={reIndexTables}
          disabled={loading}
          variant="primary"
          className="flex flex-col gap-2 min-h-full"
        >
          <TextSearch />
          Extract AI Metadata
        </Button>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-medium dark:text-dark-text-primary">
          Current Metadata
        </h3>
        <DefogTable
          rootClassNames="!p-0"
          columns={columns}
          rows={tableData}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
          }}
          paginationPosition="bottom"
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
                className="px-3 py-2  align-top text-sm text-gray-700 dark:text-gray-200"
              >
                {cellValue}
              </td>
            );
          }}
        />

        {/* Action buttons */}
        <div className="flex justify-center my-4 gap-4">
          <Button disabled={loading} onClick={downloadMetadata}>
            <span>Download</span> <Download className="h-4 w-4" />
          </Button>

          <Button disabled={loading} onClick={uploadMetadata}>
            <span>Upload</span> <Upload className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default MetadataTable;
