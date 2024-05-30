import React, { useContext } from "react";
import { GoogleLogin, GoogleOAuthProvider } from "@react-oauth/google";
import { Alert, message } from "antd";
import { Context } from "./Context";
import { useRouter } from "next/router";
import setupBaseUrl from "$utils/setupBaseUrl";

const clientId =
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "REPLACE_WITH_GOOGLE_CLIENT_ID";

const GoogleLoginButton = () => {
  const [context, setContext] = useContext(Context);
  const router = useRouter();
  const onSuccess = async (response) => {
    console.log("Login Success: ", response); // Handle successful login
    const resp = await fetch(setupBaseUrl("http", "login_google"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        credential: response.credential,
      }),
    });

    if (resp.ok) {
      const data = await resp.json();

      if (data.error) {
        console.error(data.error);
        message.error(data.error);
      }

      if (data.status === "success") {
        setContext({
          user: data.user_email,
          token: data.token,
          userType: data.user_type,
        });

        localStorage.setItem("defogUser", data.user_email);
        localStorage.setItem("defogToken", data.token);
        localStorage.setItem("defogUserType", data.user_type);

        // redirect to home page
        router.push("/");
      }
    }
  };

  const onFailure = (response) => {
    console.error("Login Failed: ", response); // Handle login failure
    <Alert message={"Login Failed"} type="error" />;
  };

  return (
    <div>
      <GoogleOAuthProvider clientId={clientId}>
        <GoogleLogin
          buttonText="Log In with Google"
          onSuccess={onSuccess}
          onFailure={onFailure}
          cookiePolicy={"single_host_origin"}
        />
      </GoogleOAuthProvider>
    </div>
  );
};

export default GoogleLoginButton;
