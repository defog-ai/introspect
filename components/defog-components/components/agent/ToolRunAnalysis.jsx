import { useEffect, useState } from "react";
import { setupWebsocketManager } from "../../../../utils/websocket-manager";
import { message } from "antd";
import setupBaseUrl from "../../../../utils/setupBaseUrl";
import { LoadingOutlined } from "@ant-design/icons";

export default function ToolRunAnalysis({ question, data_csv }) {
  const [toolRunAnalysis, setToolRunAnalysis] = useState("");
  const [socketManager, setSocketManager] = useState(null);

  function onMessage(event) {
    try {
      if (!event.data) {
        message.error(
          "Something went wrong. Please try again or contact us if this persists."
        );
      }

      const response = JSON.parse(event.data);

      console.log(response);

      if (response && response.model_analysis) {
        setToolRunAnalysis((prev) => {
          return (prev ? prev : "") + response.model_analysis;
        });
      }
    } catch (error) {
      console.log(error);
    }
  }

  useEffect(() => {
    async function setup() {
      const urlToConnect = setupBaseUrl("ws", "analyse_data");
      try {
        const mgr = await setupWebsocketManager(urlToConnect, onMessage);
        setSocketManager(mgr);
        mgr.send({
          question,
          data: data_csv,
        });
      } catch (error) {
        console.log(error);
      }
    }

    setup();
  }, []);

  return (
    toolRunAnalysis.slice(0, 4) !== "NONE" && (
      <p style={{ whiteSpace: "pre-wrap" }} className="small code">
        {!toolRunAnalysis || toolRunAnalysis === "" ? (
          <>
            <LoadingOutlined /> Loading analysis...
          </>
        ) : (
          toolRunAnalysis
        )}
      </p>
    )
  );
}
