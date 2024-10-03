import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import setupBaseUrl from "$utils/setupBaseUrl";
import { message } from "antd";

const ManageUsers = () => {
  const [loading, setLoading] = useState(false);
  const [modelId, setModelId] = useState("");
  const [modelPrompt, setModelPrompt] = useState("");

  const router = useRouter();

  const getBedrockParams = async () => {
    setLoading(true);
    const token = localStorage.getItem("defogToken");
    if (!token) {
      setLoading(false);
      message.error(
        "It seems like there was no token found in your session. Please try to log in again."
      );
      return;
    }

    const res = await fetch(
      setupBaseUrl("http", "integration/get_bedrock_analysis_params"),
      {
        method: "POST",
        body: JSON.stringify({ token: token }),
        headers: { "Content-Type": "application/json" },
      }
    );
    if (res.ok) {
      const data = await res.json();
      setModelId(data.bedrock_model_id);
      setModelPrompt(data.bedrock_model_prompt);
    } else {
      message.error(
        "There was an error fetching the bedrock analysis params. Are you sure you are logged in?"
      );
    }

    setLoading(false);
  };

  useEffect(() => {
    // load from local storage
    const user = localStorage.getItem("defogUser");
    const token = localStorage.getItem("defogToken");
    const userType = localStorage.getItem("defogUserType");

    if (!user || !token || !userType) {
      // redirect to login page
      router.push("/log-in");
      return;
    }

    if (!token) {
      router.push("/log-in");
    } else {
      getBedrockParams();
    }
  }, []);

  return (
    <>
      <Meta />
      <Scaffolding id={"manage-users"} userType={"admin"}>
        <div className="flex justify-left items-left flex-col p-1 mt-5 gap-4">
          <h1 className="text-2xl ">Update Bedrock Analysis Parameters</h1>
          <p>
            Here you can update the parameters used for the bedrock analysis
            model.
          </p>
          <div className="model-id">
            <p className="text-md">
              <span className="font-bold">Model ID</span> (this is the ID of a
              model on Bedrock)
            </p>
            <input
              type="text"
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              className="border border-gray-300 p-1 w-full max-w-sm"
            />
          </div>
          <div className="model-prompt">
            <p className="text-md">
              <span className="font-bold">Model Prompt</span> (this is the
              prompt used for the model - you must include the placeholder{" "}
              <code className="text-red">&#123;sql&#125;</code>,{" "}
              <code className="text-red">&#123;question&#125;</code>, and{" "}
              <code className="text-red">&#123;data_csv&#125;</code> inside the
              prompt)
            </p>
            <textarea
              role="textbox"
              value={modelPrompt}
              onChange={(e) => setModelPrompt(e.target.value)}
              className="border border-gray-300 p-1 w-full max-h-full"
              rows={20}
            />
          </div>
          <div className="flex justify-left items-left gap-4">
            <button
              className=" bg-blue-500 border border-blue-200 text-white p-2 rounded-md"
              onClick={async () => {
                setLoading(true);
                const token = localStorage.getItem("defogToken");
                if (!token) {
                  setLoading(false);
                  message.error(
                    "It seems like there was no token found in your session. Please try to log in again."
                  );
                  return;
                }

                const res = await fetch(
                  setupBaseUrl(
                    "http",
                    "integration/set_bedrock_analysis_params"
                  ),
                  {
                    method: "POST",
                    body: JSON.stringify({
                      token: token,
                      bedrock_model_id: modelId,
                      bedrock_model_prompt: modelPrompt,
                    }),
                    headers: { "Content-Type": "application/json" },
                  }
                );
                if (res.ok) {
                  message.success(
                    "Successfully updated bedrock analysis params!"
                  );
                } else {
                  message.error(
                    "There was an error updating the bedrock analysis params. Are you sure you are logged in?"
                  );
                }

                setLoading(false);
              }}
            >
              {loading ? "Loading..." : "Update Bedrock Analysis Params"}
            </button>
          </div>
        </div>
      </Scaffolding>
    </>
  );
};

export default ManageUsers;
