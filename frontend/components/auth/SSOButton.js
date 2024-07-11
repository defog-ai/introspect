import React, { useState, useContext } from "react";
import { useRouter } from "next/router";
import setupBaseUrl from "$utils/setupBaseUrl";
import { UserContext } from "$components/context/UserContext";

const SSOButton = ({ msalInstance }) => {
  const [isLoginInProgress, setIsLoginInProgress] = useState(false);
  const router = useRouter();
  const [context, setContext] = useContext(UserContext);

  const handleLogin = async () => {
    if (isLoginInProgress) {
      return;
    }

    setIsLoginInProgress(true);
    try {
      // Login via a popup
      const loginResponse = await msalInstance.loginPopup({
        scopes: ["user.read"], // Replace with the scopes you need
      });

      const idToken = loginResponse?.idToken;

      // Handle post-login actions
      console.log("Login successful!");
      // send the user's id token to the server
      // if successful, save the token to local storage
      // in the user does not exist on the server side, create the user and return the token
      // if the user exists, just return the token
      const urlToUse = setupBaseUrl("http", "validate_ms_sso");
      const resp = await fetch(urlToUse, {
        method: "POST",
        body: JSON.stringify({ token: idToken }),
        headers: {
          "Content-Type": "application/json",
        },
      });
      const data = await resp.json();
      setIsLoginInProgress(false);
      if (data.status === "success") {
        // set context
        setContext({
          user: data.user,
          token: data.token,
          userType: data.user_type,
        });
        // save to local storage
        localStorage.setItem("defogUser", data.user);
        localStorage.setItem("defogToken", data.token);
        localStorage.setItem("defogUserType", data.user_type);

        // redirect to home page
        router.push("/");
      }
    } catch (error) {
      console.error(error);
    }
    setIsLoginInProgress(false);
  };

  return <button onClick={handleLogin}>Sign In with Microsoft</button>;
};

export default SSOButton;
