import React, { useMemo } from "react";
import { Trash2 } from "lucide-react";
import { Table, Tabs } from "@defogdotai/agents-ui-components/core-ui";

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

interface TabProps {
  name: string;
  content?: any;
  classNames?: string;
  headerClassNames?: string;
}

const TableComponent: React.FC<TableComponentProps> = ({
  name,
  description,
  columns,
  rows,
}) => {
  // Format columns + keys for Defog Table
  const columnsWithIndex = columns.map((column) => ({
    title: column,
    dataIndex: column,
  }));

  const rowsWithColumnKeys = rows.map((row) => {
    return row.reduce((acc, value, index) => {
      acc[columns[index]] = value;
      return acc;
    }, {});
  });

  return (
    <div>
      <p className="text-sm text-gray-500 italic mt-2 mb-3">{description}</p>
      <Table columns={columnsWithIndex} rows={rowsWithColumnKeys} />
    </div>
  );
};

const Source: React.FC<SourceProps> = ({ link, source, deleteSource }) => {
  const tabs = useMemo<TabProps[]>(() => {
    return source.tables.map((table, index) => {
      const displayName = table?.name?.replace("imported.", "") || table.name;
      return {
        name: displayName,
        content: <TableComponent key={index} {...table} />,
      };
    });
  }, [source]);

  return (
    <div key={link}>
      {/* Title Row */}
      <div className="flex">
        <a
          target="_blank"
          rel="noopener noreferrer"
          href={link}
          className="text-2xl font-bold"
        >
          {source.source_title ? source.source_title : link}
        </a>
        <Trash2
          className="ml-auto cursor-pointer"
          onClick={() => deleteSource(link)}
        />
      </div>

      {/* Summary */}
      <p className="mt-2 text-gray-600">{source.source_summary}</p>

      {/* If we have tables */}
      {source.tables.length > 0 && (
        <h2 className="text-xl font-semibold mt-4 mb-4">Imported Tables</h2>
      )}

      {source.tables.length > 0 && (
        <Tabs size="small" tabs={tabs} defaultSelected={source.tables[0].name} />
      )}

      <hr className="my-4 border-gray-300 dark:border-gray-700" />
    </div>
  );
};

export default Source;
