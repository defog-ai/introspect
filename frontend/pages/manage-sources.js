import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import Source from "$components/manage-sources/Source";
import setupBaseUrl from "$utils/setupBaseUrl";
import { useCallback, useContext, useEffect, useState } from "react";
import { Book } from "lucide-react";
import {
  Button,
  Input as DefogInput,
  SingleSelect,
  SpinningLoader,
  MessageManagerContext,
} from "@defogdotai/agents-ui-components/core-ui";

const ManageSources = () => {
  const [apiKeyName, setApiKeyName] = useState(null);
  const [apiKeyNames, setApiKeyNames] = useState([]);
  const [inputLink, setInputLink] = useState("");
  const [importedSources, setImportedSources] = useState([]);
  const [waitImport, setWaitImport] = useState(false);
  const message = useContext(MessageManagerContext);

  const getApiKeyNames = async (token) => {
    try {
      const res = await fetch(
        (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_db_names",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        }
      );
      if (!res.ok) {
        throw new Error("Failed to get api key names. Check your network?");
      }
      const data = await res.json();
      setApiKeyNames(data.db_names || []);
      setApiKeyName(data.db_names?.[0] || null);
    } catch (e) {
      message.error(e.message);
      console.error(e);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    getApiKeyNames(token);
  }, []);

  const getSources = useCallback(async () => {
    if (!apiKeyName) return;
    try {
      const token = localStorage.getItem("defogToken");
      const response = await fetch(setupBaseUrl("http", `sources/list`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, key_name: apiKeyName }),
      });

      if (!response.ok) {
        message.error("Failed to get sources");
        return;
      }
      const data = await response.json();
      setImportedSources(data);
    } catch (e) {
      message.error(e.message);
      console.error(e);
    }
  }, [apiKeyName, message]);

  useEffect(() => {
    getSources();
  }, [apiKeyName, getSources]);

  const addSource = useCallback(async () => {
    try {
      const token = localStorage.getItem("defogToken");
      setWaitImport(true);

      const response = await fetch(setupBaseUrl("http", `sources/import`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          key_name: apiKeyName,
          links: [inputLink],
        }),
      });

      if (!response.ok) {
        message.error("Failed to add source");
        return;
      }
      message.info("Source added successfully");
      setInputLink("");
      getSources();
    } catch (e) {
      message.error("Failed to add source");
      console.error(e);
    } finally {
      setWaitImport(false);
    }
  }, [apiKeyName, inputLink, getSources, message]);

  const deleteSource = useCallback(
    async (link) => {
      try {
        const token = localStorage.getItem("defogToken");
        const response = await fetch(setupBaseUrl("http", `sources/delete`), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, key_name: apiKeyName, link }),
        });
        if (!response.ok) {
          message.error("Failed to delete source");
          return;
        }
        message.info("Source deleted successfully");
        getSources();
      } catch (e) {
        message.error("Error deleting source");
        console.error(e);
      }
    },
    [apiKeyName, getSources, message]
  );

  return (
    <>
      <Meta />
      <Scaffolding id="manage-users" userType="admin">
        {apiKeyNames.length > 1 && (
          <div className="w-full mb-4">
            <SingleSelect
              options={apiKeyNames.map((item) => ({
                value: item,
                label: item,
              }))}
              value={apiKeyName}
              onChange={(val) => setApiKeyName(val)}
              placeholder="Select an API key"
              rootClassNames="w-full"
            />
          </div>
        )}

        <div className="flex flex-col items-center justify-center p-1 mt-5">
          <h1>
            <Book size={48} color="#1890ff" />
          </h1>
          <h1 className="text-3xl mt-4">Manage Sources</h1>
        </div>

        <div className="flex flex-col items-center p-1 mt-4 w-full">
          <div className="flex items-center w-full px-4 my-2">
            <DefogInput
              value={inputLink}
              onChange={(e) => setInputLink(e.target.value)}
              placeholder="Enter source link here"
              /** 
               * Provide custom classes to enlarge the input:
               */
              size="default"
              rootClassNames="flex-grow w-full"
              inputClassNames="p-3 border border-gray-300 rounded-lg text-gray-700 focus:outline-none w-full"
            />
            <div className="ml-4">
              {waitImport ? (
                <SpinningLoader classNames="text-blue-600 w-6 h-6" />
              ) : (
                <Button variant="primary" onClick={addSource}>
                  Add Source
                </Button>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-col p-1 mt-2">
          {Object.entries(importedSources).map(([link, source]) => (
            <Source
              key={link}
              link={link}
              source={source}
              deleteSource={deleteSource}
            />
          ))}
        </div>
      </Scaffolding>
    </>
  );
};

export default ManageSources;
