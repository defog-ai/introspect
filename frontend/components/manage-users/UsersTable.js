import { Button, SpinningLoader, Table, MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";
import { Trash2, UserCheck, UserX, Key } from "lucide-react";
import setupBaseUrl from "$utils/setupBaseUrl";
import { useContext, useState } from "react";

const UsersTable = ({ userDets, getUserDets, loading, setLoading }) => {
  const message = useContext(MessageManagerContext);
  const [resetPasswordUser, setResetPasswordUser] = useState(null);
  const [newPassword, setNewPassword] = useState("");

  const showDeleteConfirm = async (username) => {
    if (confirm(`Are you sure you want to delete user ${username}?`)) {
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
        message.error(data.message || "There was an error deleting the user. Please try again.");
      }
      await getUserDets();
      setLoading(false);
    }
  };

  const toggleUserStatus = async (username, currentStatus) => {
    const newStatus = currentStatus === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    setLoading(true);
    const token = localStorage.getItem("defogToken");
    
    try {
      const res = await fetch(setupBaseUrl("http", `admin/update_user_status`), {
        method: "POST",
        body: JSON.stringify({
          username,
          status: newStatus,
          token,
        }),
        headers: { "Content-Type": "application/json" },
      });
      
      const data = await res.json();
      
      if (data.status === "success") {
        message.success(`User status updated to ${newStatus}`);
      } else {
        message.error(data.message || "Failed to update user status");
      }
    } catch (error) {
      message.error("An error occurred while updating user status");
      console.error(error);
    } finally {
      await getUserDets();
      setLoading(false);
    }
  };

  const resetPassword = async (e) => {
    e.preventDefault();
    if (!resetPasswordUser) return;
    
    setLoading(true);
    const token = localStorage.getItem("defogToken");
    
    try {
      const res = await fetch(setupBaseUrl("http", `admin/reset_password`), {
        method: "POST",
        body: JSON.stringify({
          username: resetPasswordUser,
          password: newPassword,
          token,
        }),
        headers: { "Content-Type": "application/json" },
      });
      
      const data = await res.json();
      
      if (data.status === "success") {
        message.success("Password reset successfully");
        setResetPasswordUser(null);
        setNewPassword("");
      } else {
        message.error(data.detail || data.message || "Failed to reset password");
      }
    } catch (error) {
      message.error("An error occurred while resetting password");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "Never";
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const columns = [
    {
      title: "Username",
      dataIndex: "username",
      key: "username",
      width: "25%",
      sorter: (a, b) => a.username.localeCompare(b.username),
    },
    {
      title: "User Type",
      dataIndex: "user_type",
      key: "user_type",
      width: "10%",
      sorter: (a, b) => a.user_type.localeCompare(b.user_type),
      render: (value) => (
        <span className={value === "ADMIN" ? "text-blue-600 dark:text-blue-400 font-semibold" : ""}>
          {value}
        </span>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: "10%",
      sorter: (a, b) => a.status.localeCompare(b.status),
      render: (value) => (
        <span className={
          value === "ACTIVE" 
            ? "text-green-600 dark:text-green-400 font-semibold" 
            : "text-red-600 dark:text-red-400 font-semibold"
        }>
          {value}
        </span>
      ),
    },
    {
      title: "Created At",
      dataIndex: "created_at",
      key: "created_at",
      width: "15%",
      sorter: (a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0),
      render: (value) => formatDate(value),
    },
    {
      title: "Last Login",
      dataIndex: "last_login",
      key: "last_login",
      width: "15%",
      sorter: (a, b) => new Date(a.last_login || 0) - new Date(b.last_login || 0),
      render: (value) => formatDate(value),
    },
    {
      title: "Actions",
      dataIndex: "__actions",
      key: "actions",
      width: "25%",
      render: (_, row) => (
        <div className="flex gap-2">
          <Button
            variant="normal"
            icon={row.status === "ACTIVE" ? <UserX size={18} /> : <UserCheck size={18} />}
            onClick={() => toggleUserStatus(row.username, row.status)}
            className="hover:bg-gray-100 dark:hover:bg-gray-700"
            tooltip={row.status === "ACTIVE" ? "Deactivate User" : "Activate User"}
          />
          <Button
            variant="normal"
            icon={<Key size={18} />}
            onClick={() => setResetPasswordUser(row.username)}
            className="hover:bg-gray-100 dark:hover:bg-gray-700"
            tooltip="Reset Password"
          />
          <Button
            variant="normal"
            icon={<Trash2 size={18} />}
            onClick={() => showDeleteConfirm(row.username)}
            className="hover:bg-gray-100 dark:hover:bg-gray-700 text-red-500"
            tooltip="Delete User"
          />
        </div>
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
              Processing User Action
            </span>
          </div>
        )}
        
        {resetPasswordUser && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-xl w-1/3">
              <h3 className="text-lg font-semibold mb-4 dark:text-white">Reset Password</h3>
              <form onSubmit={resetPassword}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Username
                  </label>
                  <input
                    type="text"
                    value={resetPasswordUser}
                    disabled
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md p-2 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                  />
                </div>
                
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    New Password
                  </label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md p-2 dark:bg-gray-700 dark:text-white"
                    placeholder="Enter new password"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Password must be at least 8 characters with uppercase, lowercase, number, and special character.
                  </p>
                </div>
                
                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setResetPasswordUser(null);
                      setNewPassword("");
                    }}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    disabled={!newPassword || newPassword.length < 8}
                  >
                    Reset Password
                  </button>
                </div>
              </form>
            </div>
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
            showSizeChanger: true,
            pageSizeOptions: [10, 20, 50],
          }}
          paginationPosition="bottom"
          showSearch={true}
          searchPlaceholder="Search by username..."
          searchFields={["username"]}
        />
      </div>
    </div>
  );
};

export default UsersTable;
