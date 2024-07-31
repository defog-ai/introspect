import { useState, useEffect } from "react";
import { Form, Input, Button, Select, message } from "antd";
import { IdcardOutlined } from "@ant-design/icons";
import setupBaseUrl from "$utils/setupBaseUrl";
import "tailwindcss/tailwind.css";
import { csv } from "d3";

const { Option } = Select;

const AddUsersCSVForm = ({ loading, context, getUserDets, setLoading }) => {
  const [users, setUsers] = useState([
    { username: "", password: "", userType: "" },
  ]);
  const [csvString, setCsvString] = useState("username,password,user_type\n");

  useEffect(() => {
    const csv = users
      .filter((user) => user.username && user.password && user.userType)
      .map((user) => `${user.username},${user.password},${user.userType}`)
      .join("\n");
    setCsvString(`username,password,user_type\n${csv}`);
  }, [users]);

  const handleChange = (index, field, value) => {
    const newUsers = [...users];
    newUsers[index][field] = value;
    setUsers(newUsers);
    console.log(csvString);
  };

  const handleSubmit = async () => {
    setLoading(true);
    const res = await fetch(setupBaseUrl("http", `admin/add_users_csv`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ users_csv: csvString, token: context.token }),
    });
    const data = await res.json();
    if (data.status === "success") {
      message.success("Users added successfully! Refreshing the user data...");
      setUsers([{ username: "", password: "", userType: "" }]); // Clear the form values
    } else {
      message.error("There was an error adding the users. Please try again.");
    }
    await getUserDets();
    setLoading(false);
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
              className="w-1/3"
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
              label="Password"
              name={`password${index}`}
              required
              className="w-1/3"
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
              className="w-1/3"
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
          </div>
        ))}
        <Button
          type="dashed"
          onClick={() =>
            setUsers([...users, { username: "", password: "", userType: "" }])
          }
          block
        >
          Add Another User
        </Button>
        {csvString.trim() !== "username,password,user_type" && (
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
            disabled={csvString.trim() === "username,password,user_type"}
          >
            Add Users
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default AddUsersCSVForm;
