import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import { Spin } from "antd";

const QueryDatabase = () => {
  const [userType, setUserType] = useState("");
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // load from local storage and set context
    const user = localStorage.getItem("defogUser");
    const token = localStorage.getItem("defogToken");
    const userType = localStorage.getItem("defogUserType");

    if (!user || !token || !userType) {
      // redirect to login page
      router.push("/log-in");
      return;
    }

    setUserType(userType);
    setLoading(false);
    if (userType === "admin") {
      console.log("redirecting to extract metadata..");
      router.push("/extract-metadata");
    } else {
      console.log("redirecting to query data..");
      router.push("/query-data");
    }
  }, []);

  return (
    <>
      <Meta />
      <Scaffolding userType={userType}>
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-md w-full space-y-8 p-10 bg-white rounded-xl shadow-md">
            <div className="text-center">
              <h1 className="text-3xl font-semibold text-gray-900 mb-4">
                Welcome to Defog!
              </h1>
              <h3 className="text-lg text-gray-700">
                Please wait while we log you in and redirect you to the right
                page... <Spin />
              </h3>
            </div>
            {loading && (
              <div className="flex justify-center mt-6">
                <svg
                  className="animate-spin h-5 w-5 text-indigo-600"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              </div>
            )}
          </div>
        </div>
      </Scaffolding>
    </>
  );
};

export default QueryDatabase;
