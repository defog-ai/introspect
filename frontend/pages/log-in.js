import React, { useContext } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import { Input, Form, Button, message } from "antd";
import { UserContext } from "$components/context/UserContext";
import Scaffolding from "$components/layout/Scaffolding";
import GoogleLoginButton from "$components/auth/GoogleLogin";

const LogIn = () => {
  const [context, setContext] = useContext(UserContext);
  const router = useRouter();

  const handleLogin = async (values) => {
    console.log("test");
    const urlToUse = (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/login";
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
    } else {
      message.error("Login failed. Please contact your administrator.");
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

        <GoogleLoginButton />
      </Scaffolding>
    </>
  );
};

export default LogIn;
