// create a simple login page with React, Ant Design, and Next.js

import React, { useContext, useState, useEffect } from "react";
import { useRouter } from "next/router";
import Meta from "../components/common/Meta";
import Scaffolding from "../components/common/Scaffolding";
import { Context } from "../components/common/Context";
import { Input, Form, Button } from "antd";
import setupBaseUrl from "../utils/setupBaseUrl";
import SSOButton from "../components/common/SSOButton";
import { PublicClientApplication } from "@azure/msal-browser";

const LogIn = () => {
  const [context, setContext] = useContext(Context);
  const [instance, setInstance] = useState(null);
  const router = useRouter();

  useEffect(() => {
    async function init() {
      const msalConfig = {
        auth: {
          clientId: `${process.env.NEXT_PUBLIC_MSAL_CLIENT_ID}`,
          authority: `https://login.microsoftonline.com/${process.env.NEXT_PUBLIC_MSAL_TENANT_ID}`,
          redirectUri: `${process.env.NEXT_PUBLIC_MSAL_REDIRECT_URI}`,
        },
      };

      const msalInstance =
        await PublicClientApplication.createPublicClientApplication(msalConfig);
      setInstance(msalInstance);
    }
    init();
  }, []);

  const handleLogin = async (values) => {
    const urlToUse = setupBaseUrl("http", "login");
    const response = await fetch(urlToUse, {
      method: "POST",
      body: JSON.stringify(values),
    });

    const data = await response.json();
    if (data.status === "success") {
      // set context
      setContext({
        user: values.username,
        token: data.token,
        userType: data.user_type,
      });
      // save to local storage
      localStorage.setItem("defogUser", values.username);
      localStorage.setItem("defogToken", data.token);
      localStorage.setItem("defogUserType", data.user_type);

      // redirect to home page
      router.push("/");
    }
  };

  return (
    <>
      <Meta />
      <Scaffolding>
        <h1 style={{ paddingBottom: "1em" }}>Welcome to Defog!</h1>
        {/* Login with antd components */}
        <Form
          labelCol={{ span: 4 }}
          wrapperCol={{ span: 20 }}
          style={{ maxWidth: 800 }}
          onFinish={handleLogin}
        >
          <Form.Item label="Username" name="username">
            <Input />
          </Form.Item>
          <Form.Item label="Password" name="password">
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              Log In
            </Button>
          </Form.Item>
        </Form>

        {/* Login with MSAL */}
        {instance ? <SSOButton msalInstance={instance} /> : null}
      </Scaffolding>
    </>
  );
};

export default LogIn;
