import React from "react";
import { DeleteOutlined } from "@ant-design/icons";
import { Divider } from "antd";
import { Table } from "@defogdotai/agents-ui-components/core-ui";

interface SourceProps {
  link: string;
  source: {
    source_title?: string;
    source_summary: string;
    tables: TableComponentProps[];
  };
  deleteSource: (link: string) => void;
}

interface TableComponentProps {
  name: string;
  description: string;
  columns: string[];
  rows: string[][];
}

const TableComponent: React.FC<TableComponentProps> = ({ name, description, columns, rows }) => {
  const displayName = name.replace("imported.", "");
  // format columns and keys for Table component
  const columnsWithIndex = columns.map((column) => ({ title: column, dataIndex: column }));
  const rowsWithColumnKeys = rows.map((row) => {
    return row.reduce((acc, value, index) => {
      acc[columns[index]] = value;
      return acc;
    }, {});
  })

  return (
    <div>
      <h3 className="text-l text-gray-600 mt-3">{displayName}</h3>
      <p className="text-s text-gray-500 italic mt-2 mb-3">{description}</p>
      <Table columns={columnsWithIndex} rows={rowsWithColumnKeys} />
    </div>
  );
};

const Source: React.FC<SourceProps> = ({ link, source, deleteSource }) => {
  return (
    <div key={link}>
      <div className="flex">
        <a
          target="_blank"
          rel="noopener noreferrer"
          href={link}
          className="text-2xl text-bold"
        >
          {source.source_title ? source.source_title : link}
        </a>
        <DeleteOutlined className="ml-auto" onClick={() => deleteSource(link)} />
      </div>
      <div>
        <p className="mt-2 text-gray-600">{source.source_summary}</p>
      </div>
      {source.tables.length > 0 && <h2 className="text-xl font-semibold mt-4">Imported Tables</h2>}
      {source.tables.map((table, index) => (
        <TableComponent key={index} {...table} />
      ))}
      <Divider />
    </div>
  );
};

export default Source;