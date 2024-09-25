import { useState, useEffect } from "react";
import { Alert, Form, Select, Input, Button, Table, message, Spin } from "antd";
import {
  EditOutlined,
  SaveOutlined,
  TableOutlined,
  DownloadOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import setupBaseUrl from "$utils/setupBaseUrl";

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
  const [selectedTablesForIndexing, setSelectedTablesForIndexing] = useState(
    []
  );
  const [metadata, setMetadata] = useState(initialMetadata);
  const [filteredMetadata, setFilteredMetadata] = useState(initialMetadata);

  // key (table_name_column_name): value (boolean to toggle editing of the column descritpion)
  const [editingKeys, setEditingKeys] = useState({});

  const [loading, setLoading] = useState(false);
  const [desc, setDesc] = useState({});
  const [filter, setFilter] = useState([]); // list of table names to filter
  const [form] = Form.useForm();

  const [pageSize, setPageSize] = useState(10);

  const hasNonEmptyDescriptionFunction = (metadata) => {
    return metadata.some(
      (item) => item.column_description && item.column_description.trim() !== ""
    );
  };

  useEffect(() => {
    if (tablesData) {
      setTables(tablesData.tables);
      setSelectedTablesForIndexing(tablesData.indexed_tables);
      form.setFieldsValue({ tables: tablesData.indexed_tables });
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
      body: JSON.stringify({
        token,
        key_name: apiKeyName,
      }),
    });
    // check if the response has status 200
    if (res.status === 401) {
      message.error("Your credentials are incorrect. Please log in again.");
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
          body: JSON.stringify({
            metadata: metadata,
            token: token,
            key_name: apiKeyName,
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
    // Reapply the filter if there's an active filter, otherwise set filteredMetadata to updatedMetadata
    if (filter.length > 0) {
      const filtered = updatedMetadata.filter((item) =>
        filter.some((f) => item.table_name.includes(f))
      );
      setFilteredMetadata(filtered);
    } else {
      setFilteredMetadata(updatedMetadata);
    }
  };

  const reIndexTables = async (values) => {
    setLoading(true);
    try {
      message.info(
        "Extracting metadata from selected tables. This can take up to 5 minutes. Please be patient."
      );
      const res = await fetch(
        setupBaseUrl("http", `integration/generate_metadata`),
        {
          method: "POST",
          body: JSON.stringify({
            tables: values.tables,
            token: token,
            key_name: apiKeyName,
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
  ];

  const columns = [
    {
      title: (
        <div>
          <div>Table Name</div>
          <Select
            mode="multiple"
            showSearch
            placeholder="Filter tables"
            optionFilterProp="children"
            onChange={handleFilterChange}
            allowClear={true}
            className="w-full mt-1 focus:outline-none focus:ring-0"
            options={[
              ...uniqueTableNames.map((table) => ({
                value: table,
                label: table,
              })),
            ]}
          />
        </div>
      ),
      dataIndex: "table_name",
      key: "table_name",
      width: "20%",
      align: "center",
      render: (text) => <span className="font-bold">{text}</span>,
    },
    {
      title: "Column Name",
      dataIndex: "column_name",
      key: "column_name",
      width: "20%",
      align: "center",
      render: (text) => <span className="font-semibold">{text}</span>,
    },
    {
      title: "Data Type",
      dataIndex: "data_type",
      key: "data_type",
      width: "20%",
      align: "center",
      render: (text) => <span className="font-mono">{text}</span>,
    },
    {
      title: "Description",
      dataIndex: "column_description",
      key: "column_description",
      width: "35%",
      align: "center",
      render: (text, record) => {
        const key = `${record.table_name}_${record.column_name}`;
        return editingKeys[key] ? (
          <Input.TextArea
            defaultValue={text}
            onChange={(e) => handleInputChange(e, key)}
            autoSize={{ minRows: 2, maxRows: 4 }}
          />
        ) : (
          <span className="italic p-1">{text}</span>
        );
      },
    },
    {
      key: "action",
      width: "5%",
      align: "center",
      render: (text, record) => {
        const key = `${record.table_name}_${record.column_name}`;
        return editingKeys[key] ? (
          <SaveOutlined onClick={() => toggleEdit(key)} />
        ) : (
          <EditOutlined onClick={() => toggleEdit(key)} />
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
    form.setFieldsValue({ tables: tables });
  };

  const clearAllTables = () => {
    setSelectedTablesForIndexing([]);
    form.setFieldsValue({ tables: [] });
  };

  const downloadMetadata = async () => {
    // download metadata as a CSV
    const response = await fetch(
      setupBaseUrl("http", `integration/get_metadata`),
      {
        method: "POST",
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
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
      // remove the link
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
      // get the file content as a text file

      const reader = new FileReader();
      reader.onload = async (e) => {
        const metadataCsv = e.target.result;
        const response = await fetch(
          setupBaseUrl("http", `integration/upload_metadata`),
          {
            method: "POST",
            body: JSON.stringify({
              token: token,
              key_name: apiKeyName,
              metadata_csv: metadataCsv,
            }),
          }
        );
        if (!response.ok) {
          // get the JSON response
          const resp = await response.json();
          message.error(resp.error || "Error uploading metadata", 10);
          return;
        } else {
          message.success("Metadata uploaded successfully! Reloading...");

          // reload metadata
          await fetchMetadata();
        }
      };

      reader.readAsText(file);
    };

    setLoading(true);
    fileInput.click();
    setLoading(false);
  };

  return (
    <div className="mx-auto bg-white shadow-md rounded-md p-6">
      <div className="flex flex-col items-center text-2xl mb-10">
        <TableOutlined className="text-4xl mb-2" />
        <span>View and Update Metadata</span>
      </div>
      <Form
        className="flex flex-col w-full mb-4"
        form={form}
        onFinish={reIndexTables}
      >
        <Form.Item
          className="w-full"
          label="Select tables"
          name="tables"
          initialValue={selectedTablesForIndexing}
        >
          <Select
            mode="tags"
            placeholder="Add tables to index"
            onChange={setSelectedTablesForIndexing}
            options={(tables || []).map((table) => ({
              value: table,
              label: table,
            }))}
            dropdownRender={(menu) => (
              <>
                <div
                  style={{ padding: "8px", justifyContent: "space-between" }}
                >
                  <button
                    type="button"
                    className="mr-4 px-4 py-1 bg-gray-100 border border-gray-300 rounded-md shadow-sm hover:bg-gray-200 transition-colors duration-200"
                    onClick={addAllTables}
                  >
                    Add All ➕
                  </button>
                  <button
                    type="button"
                    className="px-4 py-1 bg-gray-100 border border-gray-300 rounded-md shadow-sm hover:bg-gray-200 transition-colors duration-200"
                    onClick={clearAllTables}
                  >
                    Clear All ❌
                  </button>
                </div>
                <hr style={{ margin: "4px 0" }} />
                {menu}
              </>
            )}
          />
        </Form.Item>
        <Button
          type="dashed"
          htmlType="submit"
          className="w-64 bg-white border border-gray-300 text-blue-500 hover:bg-blue-500 hover:text-white self-center"
        >
          Extract Table Metadata
        </Button>
      </Form>
      {loading ? (
        <div className="flex justify-center items-center">
          <Spin size="large" tip="Fetching metadata..." />
        </div>
      ) : (
        <>
          <div className="flex justify-center my-4 gap-4">
            <Button
              className="rounded bg-blue-600 px-2 py-1 text-xs font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              loading={loading}
              onClick={updateMetadata}
            >
              Save Changes
            </Button>

            <Button
              className="rounded px-2 py-1 text-xs font-semibold text-black shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              loading={loading}
              onClick={downloadMetadata}
            >
              Download <DownloadOutlined />
            </Button>

            <Button
              className="rounded px-2 py-1 text-xs font-semibold text-black shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              loading={loading}
              onClick={uploadMetadata}
            >
              Upload <UploadOutlined />
            </Button>
          </div>
          <Alert
            message="This table is a preview for your changes. Please hit 'Save Changes' to update metadata on the defog server, or upload your metadata as a CSV"
            type="info"
            showIcon
            className="mb-4"
          />

          <Table
            columns={columns}
            dataSource={tableData}
            pagination={{
              pageSize: pageSize,
              pageSizeOptions: ["10", "20", "50", "100"],
              showSizeChanger: true,
              position: ["bottomCenter"], // Position of the pagination
            }}
            scroll={{ y: 1200 }}
            onChange={(pagination) => {
              setPageSize(pagination.pageSize);
            }}
          />
        </>
      )}
    </div>
  );
};

export default MetadataTable;
