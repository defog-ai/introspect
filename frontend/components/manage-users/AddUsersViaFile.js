import React, { useState, useEffect, useContext } from "react";
import { Form, Input, Button, Upload, Typography } from "antd";
import { FileAddOutlined, UploadOutlined } from "@ant-design/icons";
import setupBaseUrl from "$utils/setupBaseUrl";
import Papa from "papaparse";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";

const { Title } = Typography;

const AddUsersViaFile = ({ loading, getUserDets }) => {
  const [users, setUsers] = useState([
    { username: "", password: "", userType: "" },
  ]);
  const [csvString, setCsvString] = useState("username,password,user_type\n");
  const [googleSheetsUrl, setGoogleSheetsUrl] = useState("");
  const [isFileUploaded, setFileUploaded] = useState(false);
  const message = useContext(MessageManagerContext);

  useEffect(() => {
    const csv = users
      .filter((user) => user.username && user.password && user.userType)
      .map((user) => `${user.username},${user.password},${user.userType}`)
      .join("\n");
    setCsvString(`username,password,user_type\n${csv}`);
  }, [users]);

  useEffect(() => {
    const csv = users
      .filter((user) => user.username && user.password && user.userType)
      .map((user) => `${user.username},${user.password},${user.userType}`)
      .join("\n");
    setCsvString(`username,password,user_type\n${csv}`);
  }, [users]);

  const handleFileUpload = (file) => {
    Papa.parse(file, {
      error: (error) => {
        message.error("There was an error parsing the CSV file.");
      },
      complete: (results) => {
        const parsedData = results.data.map((row) => ({
          username: row.username,
          password: row.password,
          userType: row.user_type,
        }));
        setUsers(parsedData);
        setFileUploaded(true);
        setGoogleSheetsUrl("");
        message.success(
          "CSV file parsed successfully. Please hit 'Add Users' to proceed."
        );
      },
      header: true,
      skipEmptyLines: true,
    });
    return false;
  };

  const handleSubmit = async (values) => {
    // this assumes user has chosen one of the two options: googleSheetsUrl or upload CSV file
    try {
      const endpoint = "admin/add_users";
      const token = localStorage.getItem("defogToken");

      const payload =
        csvString.trim() !== "username,password,user_type"
          ? { users_csv: csvString, token: token }
          : { ...values, token: token };

      const res = await fetch(setupBaseUrl("http", endpoint), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();

      if (data.status === "success") {
        message.success(
          "Users added successfully! Refreshing the user data..."
        );
        setUsers([{ username: "", password: "", userType: "" }]);
      } else {
        throw new Error(data.message || "There was an error adding the users.");
      }
      await getUserDets();
    } catch (error) {
      console.error("Error:", error);
      message.error(
        error.message ||
          "There was an error adding the users. Please try again."
      );
    } finally {
      setFileUploaded(false);
      setCsvString("username,password,user_type\n");
    }
  };

  return (
    <div className="w-3/4 p-6 border border-gray-200 rounded-lg shadow-lg">
      <h1 className="text-center text-2xl mb-8">
        <FileAddOutlined className="mr-2" />
        Add Users via File
      </h1>

      <Form layout="vertical" disabled={loading} onFinish={handleSubmit}>
        <Title level={4} className="mt-6">
          Upload CSV File
        </Title>
        <Form.Item
          label={
            isFileUploaded
              ? ""
              : "Expected columns in the file: username,password,user_type,allowed_dbs. For users that must login via SSO, please set the password column to blank."
          }
        >
          <Upload
            beforeUpload={handleFileUpload}
            accept=".csv"
            showUploadList={false}
            disabled={isFileUploaded}
          >
            <Button icon={<UploadOutlined />} disabled={isFileUploaded}>
              {isFileUploaded ? "Uploaded" : "Upload CSV"}
            </Button>
          </Upload>
        </Form.Item>

        <Title level={4}>
          Or a paste publicly accessible Google Sheets URL
        </Title>
        <Form.Item label="Google Sheets URL" name="gsheets_url">
          <Input
            className="pd-2"
            value={googleSheetsUrl}
            onChange={(e) => setGoogleSheetsUrl(e.target.value)}
          />
        </Form.Item>

        {isFileUploaded && (
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
            className="w-1/3 mx-auto block"
            disabled={
              csvString.trim() === "username,password,user_type" &&
              !googleSheetsUrl
            }
          >
            Add Users
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default AddUsersViaFile;
