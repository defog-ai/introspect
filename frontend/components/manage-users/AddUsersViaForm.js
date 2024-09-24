import { useState, useEffect } from "react";
import { Form, Input, Button, Select, message } from "antd";
import { IdcardOutlined } from "@ant-design/icons";
import setupBaseUrl from "$utils/setupBaseUrl";

const { Option } = Select;

const AddUsersViaForm = ({ loading, context, getUserDets }) => {
  const [users, setUsers] = useState([
    { username: "", password: "", userType: "", userDb: [] },
  ]);
  const [csvString, setCsvString] = useState(
    "username,password,user_type,allowed_dbs\n"
  );
  const [allowedDbs, setAllowedDbs] = useState([]);

  const getApiKeyNames = async () => {
    const token = localStorage.getItem("defogToken");
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_api_key_names",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
        }),
      }
    );
    if (!res.ok) {
      throw new Error(
        "Failed to get api key names - are you sure your network is working?"
      );
    }
    const data = await res.json();
    setAllowedDbs(data.api_key_names);
  };

  useEffect(() => {
    getApiKeyNames();
    const csv = users
      .filter((user) => user.username && user.userType)
      .map(
        (user) =>
          `${user.username},${user.password || ""},${user.userType},${user.userDb.join("|")}`
      )
      .join("\n");
    setCsvString(`username,password,user_type,allowed_dbs\n${csv}`);
  }, [users]);

  const handleChange = (index, field, value) => {
    const newUsers = [...users];
    newUsers[index][field] = value;
    setUsers(newUsers);
  };

  const handleSubmit = async () => {
    const token = localStorage.getItem("defogToken");
    const res = await fetch(setupBaseUrl("http", `admin/add_users`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ users_csv: csvString, token: token }),
    });
    const data = await res.json();
    if (data.status === "success") {
      message.success("Users added successfully! Refreshing the user data...");
      setUsers([{ username: "", password: "", userType: "", userDb: [] }]); // Clear the form values
    } else {
      message.error("There was an error adding the users. Please try again.");
    }
    await getUserDets();
  };

  return (
    <div className="w-3/4 p-6 border border-gray-200 rounded-lg shadow-lg">
      <h1 className="text-center text-2xl mb-8">
        <IdcardOutlined className="mr-2" />
        Add Users Manually
      </h1>

      <Form
        layout="vertical"
        disabled={loading}
        onFinish={handleSubmit}
        className="w-full"
      >
        {users.map((user, index) => (
          <div key={index} className="flex space-x-4 mb-4">
            <Form.Item
              label="Username"
              name={`username${index}`}
              required
              className="w-1/4"
            >
              <Input
                className="border border-gray-200 h-9 rounded-md"
                value={user.username}
                onChange={(e) =>
                  handleChange(index, "username", e.target.value)
                }
              />
            </Form.Item>
            <Form.Item
              label="Password (leave blank for SSO users)"
              name={`password${index}`}
              className="w-1/4"
            >
              <Input.Password
                className="h-9"
                value={user.password}
                onChange={(e) =>
                  handleChange(index, "password", e.target.value)
                }
              />
            </Form.Item>
            <Form.Item
              label="User Type"
              name={`userType${index}`}
              required
              className="w-1/4"
            >
              <Select
                value={user.userType}
                onChange={(value) => handleChange(index, "userType", value)}
                className="h-9"
              >
                <Option value="admin">Admin</Option>
                <Option value="general">General</Option>
              </Select>
            </Form.Item>
            <Form.Item
              label="Allowed DBs (leave blank for all DBs)"
              name={`userDbs${index}`}
              required
              className="w-1/4"
            >
              <Select
                className="h-9"
                mode="multiple"
                onChange={(value) => handleChange(index, "userDb", value)}
              >
                {allowedDbs.map((db) => (
                  <Option key={db} value={db}>
                    {db}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </div>
        ))}
        <Button
          type="dashed"
          onClick={() =>
            setUsers([
              ...users,
              { username: "", password: "", userType: "", userDb: [] },
            ])
          }
          block
        >
          Add Another User
        </Button>
        {csvString.trim() !== "username,password,user_type,allowed_dbs" && (
          <Form.Item label="Generated CSV String" className="mt-4">
            <Input.TextArea
              value={csvString}
              readOnly
              autoSize={{ minRows: 2, maxRows: 4 }}
              className="font-mono border border-gray-300 bg-gray-100"
            />
          </Form.Item>
        )}
        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            className="w-1/3 mx-auto block mt-20"
            disabled={
              csvString.trim() === "username,password,user_type,allowed_dbs"
            }
          >
            Add Users
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default AddUsersViaForm;
