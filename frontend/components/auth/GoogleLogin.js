import React, { useState, useEffect, useContext } from "react";
import { GoogleLogin, GoogleOAuthProvider } from "@react-oauth/google";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";
import { useRouter } from "next/router";
import setupBaseUrl from "$utils/setupBaseUrl";
import { UserContext } from "$components/context/UserContext";

const GoogleLoginButton = () => {
  const [clientId, setClientId] = useState("");
  const [context, setContext] = useContext(UserContext);
  const message = useContext(MessageManagerContext);
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

  useEffect(() => {
    const fetchClientId = async () => {
      const res = await fetch(setupBaseUrl("http", "get_google_client_id"), {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        if (data.google_client_id) {
          setClientId(data.google_client_id);
        }
      }
    };

    fetchClientId();
  }, []);

  const onFailure = (response) => {
    console.error("Login Failed: ", response); // Handle login failure
    message.error(data.error);
  };

  return (
    <div>
      {clientId ? (
        <GoogleOAuthProvider clientId={clientId}>
          <GoogleLogin
            buttonText="Log In with Google"
            onSuccess={onSuccess}
            onFailure={onFailure}
            cookiePolicy={"single_host_origin"}
          />
        </GoogleOAuthProvider>
      ) : null}
    </div>
  );
};

export default GoogleLoginButton;
