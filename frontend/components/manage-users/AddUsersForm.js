import React from "react";
import { Form, Input, Button, message } from "antd";
import { UsergroupAddOutlined } from "@ant-design/icons";
import setupBaseUrl from "$utils/setupBaseUrl";

const AddUsersForm = ({ loading, context, getUserDets, setLoading }) => (
  <div className="w-3/4 p-6 border border-gray-200 rounded-lg shadow-lg">
    <h1 className="text-center text-2xl">
      <UsergroupAddOutlined /> Add Users{" "}
    </h1>

    <p className="mb-4 mt-4">
      Paste in user details as a CSV file with the headers:
      `username,password,user_type`
    </p>
    <Form
      name="add-users"
      disabled={loading}
      onFinish={async (values) => {
        setLoading(true);
        const res = await fetch(setupBaseUrl("http", `admin/add_users`), {
          method: "POST",
          body: JSON.stringify({ ...values, token: context.token }),
          headers: { "Content-Type": "application/json" },
        });
        const data = await res.json();
        console.log(data);
        if (data.status === "success") {
          message.success(
            "Users added successfully! Refreshing the user data..."
          );
        } else {
          message.error(
            "There was an error adding the users. Please try again."
          );
        }
        await getUserDets();
        setLoading(false);
      }}
    >
      <Form.Item label="Google Sheets URL" name="gsheets_url">
        <Input className="pd-2" />
      </Form.Item>
      <Form.Item>
        <Button type="primary" htmlType="submit" block>
          Add Users
        </Button>
      </Form.Item>
    </Form>
  </div>
);

export default AddUsersForm;
