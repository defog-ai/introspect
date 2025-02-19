import { Button, SpinningLoader, Table, MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";
import { DeleteOutlined } from "@ant-design/icons";
import setupBaseUrl from "$utils/setupBaseUrl";
import { useContext } from "react";

const UsersTable = ({ userDets, getUserDets, loading, setLoading }) => {
  const message = useContext(MessageManagerContext);

  const showDeleteConfirm = async (username) => {
    setLoading(true);
    const token = localStorage.getItem("defogToken");
    const res = await fetch(setupBaseUrl("http", `admin/delete_user`), {
      method: "POST",
      body: JSON.stringify({
        username: username,
        token: token,
      }),
      headers: { "Content-Type": "application/json" },
    });
    const data = await res.json();
    if (data.status === "success") {
      message.success("User deleted successfully! Refreshing the user data...");
    } else {
      message.error("There was an error deleting the user. Please try again.");
    }
    await getUserDets();
    setLoading(false);
  };

  const columns = [
    {
      title: "User ID",
      dataIndex: "username",
      key: "username",
      width: "30%",
    },
    {
      title: "User Type",
      dataIndex: "user_type",
      key: "user_type",
      width: "30%",
    },
    {
      title: "Allowed DBs",
      dataIndex: "allowed_dbs",
      key: "allowed_dbs",
      width: "30%",
    },
    {
      title: "Action",
      dataIndex: "__actions",
      key: "delete_user",
      width: "10%",
      render: (_, row) => (
        <Button
          variant="normal"
          icon={<DeleteOutlined />}
          onClick={() => showDeleteConfirm(row.username)}
          className="hover:bg-gray-100 dark:hover:bg-gray-700"
        />
      ),
    },
  ];

  const headerCellRender = ({ column }) => (
    <th
      key={column.key}
      className="px-6 py-3 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700"
      style={{ width: column.width }}
    >
      {column.title}
    </th>
  );

  const rowCellRender = ({
    cellValue,
    row,
    dataIndex,
    column,
  }) => {
    if (typeof column.render === "function") {
      return (
        <td
          key={row.key + "-" + dataIndex}
          className="px-6 py-4 text-left text-sm text-gray-700 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700"
        >
          {column.render(cellValue, row)}
        </td>
      );
    }
    return (
      <td
        key={row.key + "-" + dataIndex}
        className="px-6 py-4 text-left text-sm text-gray-700 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700 whitespace-nowrap"
      >
        {cellValue}
      </td>
    );
  };

  return (
    <div className="w-4/6 max-h-screen overflow-y-auto mb-4">
      <div className="relative mt-10">
        {loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/70 dark:bg-gray-900/70 backdrop-blur-[1px] z-10">
            <SpinningLoader classNames="text-blue-500 h-6 w-6" />
            <span className="mt-2 text-sm font-medium text-gray-600 dark:text-gray-300">
              Getting Latest Users Data
            </span>
          </div>
        )}
        <Table
          columns={columns}
          rows={userDets.map((user, i) => ({
            ...user,
            key: `row-${i}`,
            __origIndex: i,
          }))}
          rowCellRender={rowCellRender}
          headerCellRender={headerCellRender}
          rootClassNames="border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg bg-white dark:bg-dark-bg-secondary overflow-hidden"
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: false,
          }}
          paginationPosition="bottom"
          showSearch={false}
        />
      </div>
    </div>
  );
};

export default UsersTable;
