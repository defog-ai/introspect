import React, { useState, useEffect, useContext } from "react";
import { useRouter } from "next/router";

import Meta from "$components/layout/Meta";
import { Row, Col, Form, Input, Table, Button, Space, message } from "antd";
import setupBaseUrl from "$utils/setupBaseUrl";
import Scaffolding from "$components/layout/Scaffolding";
import { UserContext } from "$components/context/UserContext";

const ManageUsers = () => {
  const [loading, setLoading] = useState(false);
  const [userDets, setUserDets] = useState([]);
  const [context, setContext] = useContext(UserContext);

  const router = useRouter();

  const getUserDets = async () => {
    if (!context.token) {
      return;
    }

    const res = await fetch(setupBaseUrl("http", "admin/get_users"), {
      method: "POST",
      body: JSON.stringify({
        token: context.token,
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });
    const data = await res.json();
    if (data.users) {
      setUserDets(data.users);
    } else {
      message.error(
        "There was an error fetching the user data. Please try again."
      );
    }
  };

  useEffect(() => {
    let token = context.token;
    let userType = context.userType;
    if (!userType) {
      // load from local storage and set context
      const user = localStorage.getItem("defogUser");
      token = localStorage.getItem("defogToken");
      userType = localStorage.getItem("defogUserType");

      if (!user || !token || !userType) {
        // redirect to login page
        router.push("/log-in");
        return;
      }
      setContext({
        user: user,
        token: token,
        userType: userType,
      });
    }
    if (!token) {
      router.push("/log-in");
    } else {
      getUserDets();
    }
  }, [context, context.token]);

  return (
    <>
      <Meta />
      <Scaffolding id={"manage-users"} userType={"admin"}>
        <h1>Add New Users</h1>
        <Row
          gutter={{
            xs: 8,
            sm: 16,
            md: 24,
            lg: 32,
          }}
        >
          <Col span={{ xs: 24, md: 12 }}>
            <h2>Add Users</h2>
            <p>
              Paste in user details as a CSV file with the headers:
              `username,password,user_type`
            </p>
            <Form
              name="add-users"
              disabled={loading}
              onFinish={async (values) => {
                setLoading(true);
                const res = await fetch(
                  setupBaseUrl("http", `admin/add_users`),
                  {
                    method: "POST",
                    body: JSON.stringify({
                      ...values,
                      token: context.token,
                    }),
                    headers: {
                      "Content-Type": "application/json",
                    },
                  }
                );
                const data = await res.json();
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
                <Input />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit">
                  Add Users
                </Button>
              </Form.Item>
            </Form>
            <p>
              Alternatively, paste in the user details as a CSV string with the
              following headers: `username,password,user_type`
            </p>
            <Form
              name="add-users-csv"
              disabled={loading}
              onFinish={async (values) => {
                setLoading(true);
                const res = await fetch(
                  (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") +
                    `/admin/add_users_csv`,
                  {
                    method: "POST",
                    body: JSON.stringify({
                      ...values,
                      token: context.token,
                    }),
                    headers: {
                      "Content-Type": "application/json",
                    },
                  }
                );
                const data = await res.json();
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
              <Form.Item label="User Details CSV String" name="users_csv">
                <Input.TextArea
                  placeholder="username,password,user_type"
                  autoSize={{ minRows: 4, maxRows: 10 }}
                  defaultValue={`username,password,user_type\n`}
                />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit">
                  Add Users
                </Button>
              </Form.Item>
            </Form>
          </Col>
          <Col span={{ xs: 24, md: 12 }}>
            <h2>Users</h2>
            {/* display a table of all users with the headers: `username`, `user_type`, `delete_user` */}
            <Table
              dataSource={userDets}
              columns={[
                {
                  title: "User ID",
                  dataIndex: "username",
                  key: "username",
                },
                {
                  title: "User Type",
                  dataIndex: "user_type",
                  key: "user_type",
                },
                {
                  title: "Delete User",
                  key: "delete_user",
                  render: (text, record) => (
                    <Space size="middle">
                      <a
                        onClick={async () => {
                          setLoading(true);
                          const res = await fetch(
                            setupBaseUrl("http", `admin/delete_user`),
                            {
                              method: "POST",
                              body: JSON.stringify({
                                username: record.username,
                                token: context.token,
                              }),
                              headers: {
                                "Content-Type": "application/json",
                              },
                            }
                          );
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
                        }}
                      >
                        Delete
                      </a>
                    </Space>
                  ),
                },
              ]}
            />
          </Col>
        </Row>
      </Scaffolding>
    </>
  );
};

export default ManageUsers;
