import { useState, useEffect } from "react";
import { Form, Input, Button, Select, message } from "antd";
import { IdcardOutlined } from "@ant-design/icons";
import setupBaseUrl from "$utils/setupBaseUrl";

const { Option } = Select;

const AddUsersForm = ({ loading, context, getUserDets, setLoading }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [userType, setUserType] = useState("");
  const [csvString, setCsvString] = useState("username,password,user_type\n");

  useEffect(() => {
    setCsvString(
      `username,password,user_type\n${username},${password},${userType}`
    );
  }, [username, password, userType]);

  const handleSubmit = async () => {
    setLoading(true);
    const res = await fetch(setupBaseUrl("http", `admin/add_users_csv`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ users_csv: csvString, token: context.token }),
    });
    const data = await res.json();
    if (data.status === "success") {
      message.success("User added successfully! Refreshing the user data...");
      console.log(data.status);
      // Clear the form values here
      setUsername("");
      setPassword("");
      setUserType("");
    } else {
      message.error("There was an error adding the user. Please try again.");
    }
    await getUserDets();
    setLoading(false);
  };

  return (
    <div className="w-3/4 p-6 border border-gray-200 rounded-lg shadow-lg">
      <h1 className="text-center text-2xl">
        <IdcardOutlined className="mr-2" />
        Add User
      </h1>
      <Form layout="vertical" disabled={loading} onFinish={handleSubmit}>
        <Form.Item label="Username" name="username" required>
          <Input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </Form.Item>
        <Form.Item label="Password" name="password" required>
          <Input.Password
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Form.Item>
        <Form.Item label="User Type" name="user_type" required>
          <Select value={userType} onChange={(value) => setUserType(value)}>
            <Option value="admin">Admin</Option>
            <Option value="general">General</Option>
          </Select>
        </Form.Item>
        <Form.Item label="Generated CSV String">
          <Input.TextArea
            value={csvString}
            readOnly
            autoSize={{ minRows: 2, maxRows: 4 }}
          />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" block>
            Add User
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default AddUsersForm;
