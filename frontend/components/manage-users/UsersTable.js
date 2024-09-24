import { Table, Space, message, Button, Modal, Spin } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import setupBaseUrl from "$utils/setupBaseUrl";

const UsersTable = ({
  userDets,
  context,
  getUserDets,
  loading,
  setLoading,
}) => {
  const showDeleteConfirm = (username) => {
    Modal.confirm({
      title: "Are you sure you want to delete this user?",
      content: `User: ${username}`,
      okText: "Yes",
      okType: "danger",
      cancelText: "No",
      className: "w-1/3",
      onOk: async () => {
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
          message.success(
            "User deleted successfully! Refreshing the user data..."
          );
        } else {
          message.error(
            "There was an error deleting the user. Please try again."
          );
        }
        await getUserDets();
        setLoading(false);
      },
    });
  };

  return (
    <div className="w-4/6 max-h-screen overflow-y-auto mb-4">
      <Spin spinning={loading} tip="Getting Latest Users Data">
        <Table
          className="mt-10 border border-gray-200 rounded-lg shadow-lg bg-gray-100"
          dataSource={userDets}
          columns={[
            {
              title: "User ID",
              dataIndex: "username",
              key: "username",
              width: "30%",
              align: "center",
            },
            {
              title: "User Type",
              dataIndex: "user_type",
              key: "user_type",
              width: "30%",
              align: "center",
            },
            {
              title: "Allowed DBs",
              dataIndex: "allowed_dbs",
              key: "allowed_dbs",
              width: "30%",
              align: "center",
            },
            {
              title: "Action",
              key: "delete_user",
              width: "10%",
              align: "center",
              render: (text, record) => (
                <Space size="middle">
                  <Button
                    type="default"
                    icon={<DeleteOutlined />}
                    onClick={() => showDeleteConfirm(record.username)}
                  />
                </Space>
              ),
            },
          ]}
        />
      </Spin>
    </div>
  );
};

export default UsersTable;
