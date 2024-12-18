import { useState, useEffect, useContext } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import setupBaseUrl from "$utils/setupBaseUrl";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";

const ManageUsers = () => {
  const [loading, setLoading] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [userPrompt, setUserPrompt] = useState("");

  const router = useRouter();
  const message = useContext(MessageManagerContext);

  const getOpenaiParams = async () => {
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
      setupBaseUrl("http", "integration/get_openai_analysis_params"),
      {
        method: "POST",
        body: JSON.stringify({ token: token }),
        headers: { "Content-Type": "application/json" },
      }
    );
    if (res.ok) {
      const data = await res.json();
      setSystemPrompt(data.openai_system_prompt);
      setUserPrompt(data.openai_user_prompt);
    } else {
      message.error(
        "There was an error fetching the openai analysis params. Are you sure you are logged in?"
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
      getOpenaiParams();
    }
  }, []);

  return (
    <>
      <Meta />
      <Scaffolding id={"manage-users"} userType={"admin"}>
        <div className="flex justify-left items-left flex-col p-1 mt-5 gap-4">
          <h1 className="text-2xl ">Update OpenAI Analysis Parameters</h1>
          <p>
            Here you can update the parameters used for the OpenAI analysis
            model.
          </p>
          <div className="system-prompt">
            <p className="text-md">
              <span className="font-bold">System Prompt</span>
            </p>
            <textarea
              role="textbox"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="border border-gray-300 p-1 w-full max-h-full"
              rows={4}
            />
          </div>
          <div className="model-prompt">
            <p className="text-md">
              <span className="font-bold">User Prompt</span> (this is the user
              prompt used - you must include the placeholder{" "}
              <code className="text-red">&#123;sql&#125;</code>,{" "}
              <code className="text-red">&#123;question&#125;</code>, and{" "}
              <code className="text-red">&#123;data_csv&#125;</code> inside the
              prompt)
            </p>
            <textarea
              role="textbox"
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
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
                    "integration/set_openai_analysis_params"
                  ),
                  {
                    method: "POST",
                    body: JSON.stringify({
                      token: token,
                      openai_system_prompt: systemPrompt,
                      openai_user_prompt: userPrompt,
                    }),
                    headers: { "Content-Type": "application/json" },
                  }
                );
                if (res.ok) {
                  message.success(
                    "Successfully updated OpenAI analysis params!"
                  );
                } else {
                  message.error(
                    "There was an error updating the OpenAI analysis params. Are you sure you are logged in?"
                  );
                }

                setLoading(false);
              }}
            >
              {loading ? "Loading..." : "Update OpenAI Analysis Params"}
            </button>
          </div>
        </div>
      </Scaffolding>
    </>
  );
};

export default ManageUsers;
