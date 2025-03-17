import React, { useContext, useEffect, useState } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import { UserContext } from "$components/context/UserContext";
import Scaffolding from "$components/layout/Scaffolding";
import GoogleLoginButton from "$components/auth/GoogleLogin";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";

const LogIn = () => {
  const [context, setContext] = useContext(UserContext);
  const router = useRouter();
  const messageManager = useContext(MessageManagerContext);
  const [redirectMessage, setRedirectMessage] = useState("");
  const [returnUrl, setReturnUrl] = useState("");

  useEffect(() => {
    // remove analysis trees whenever on the log in page
    localStorage.removeItem("analysisTrees");
    // also remove stored analyse_data results (aka "step analysis")
    localStorage.removeItem("analyseDataResults");
    
    // Check for message in URL query parameters
    if (router.query.message) {
      setRedirectMessage(router.query.message);
      messageManager.info(router.query.message);
    }

    // Store return URL if provided
    if (router.query.returnUrl) {
      setReturnUrl(router.query.returnUrl.toString());
    }
  }, [router.query, messageManager]);

  const handleLogin = async (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    const values = Object.fromEntries(formData);

    const urlToUse = (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/login";
    const response = await fetch(urlToUse, {
      method: "POST",
      body: JSON.stringify(values),
      headers: {
        "Content-Type": "application/json",
      },
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

      // redirect to return URL if available, otherwise to reports page
      router.push(returnUrl || "/reports");
    } else {
      messageManager.error("Login failed. Please contact your administrator.");
    }
  };

  return (
    <>
      <Meta />
      <Scaffolding>
        <div className="flex min-h-full flex-1 flex-col justify-center px-6 py-12 lg:px-8 mt-16">
          <div className="sm:mx-auto sm:w-full sm:max-w-sm">
            <img
              alt="Defog.ai"
              src="/logo512.png"
              className="mx-auto h-10 w-auto"
            />
            <h2 className="mt-10 text-center text-2xl font-bold leading-9 tracking-tight text-gray-900 dark:text-dark-text-primary">
              Defog Introspect (default credentials are auto filled in)
            </h2>
            {redirectMessage && (
              <div className="mt-4 text-center text-sm text-red-600 dark:text-red-400">
                {redirectMessage}
              </div>
            )}
          </div>

          <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
            <form onSubmit={handleLogin} className="space-y-6">
              <div>
                <label
                  htmlFor="username"
                  className="block text-sm font-medium leading-6 text-gray-900 dark:text-dark-text-primary"
                >
                  Username
                </label>
                <div className="mt-2">
                  <input
                    id="username"
                    name="username"
                    type="text"
                    defaultValue={"ADMIN"}
                    required
                    autoComplete="username"
                    className="block w-full rounded-md border-0 py-1.5 text-gray-900 dark:text-dark-text-primary shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-dark-border dark:bg-dark-bg-secondary placeholder:text-gray-400 dark:placeholder:text-gray-600 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="password"
                    className="block text-sm font-medium leading-6 text-gray-900 dark:text-dark-text-primary"
                  >
                    Password
                  </label>
                  {/* <div className="text-sm">
                    <a
                      href="#"
                      className="font-semibold text-blue-600 hover:text-blue-500"
                    >
                      Forgot password?
                    </a>
                  </div> */}
                </div>
                <div className="mt-2">
                  <input
                    id="password"
                    name="password"
                    type="password"
                    required
                    autoComplete="current-password"
                    className="block w-full rounded-md border-0 py-1.5 text-gray-900 dark:text-dark-text-primary shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-dark-border dark:bg-dark-bg-secondary placeholder:text-gray-400 dark:placeholder:text-gray-600 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
                    defaultValue={"ADMIN"}
                  />
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  className="flex w-full justify-center rounded-md bg-blue-600 px-3 py-1.5 text-sm font-semibold leading-6 text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:bg-blue-700 dark:hover:bg-blue-600"
                >
                  Sign in
                </button>
              </div>
            </form>
          </div>
        </div>
      </Scaffolding>
    </>
  );
};

export default LogIn;
