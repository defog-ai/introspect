import setupBaseUrl from "../../utils/setupBaseUrl";
import { DbInfo } from "../../utils/utils";

// Define the message types for communication between the main thread and worker
type WorkerMessageData = {
  type: "UPLOAD_FILE";
  token: string;
  fileName: string;
  fileBuffer: ArrayBuffer;
};

type WorkerResponseData = {
  type: "UPLOAD_SUCCESS" | "UPLOAD_ERROR";
  dbName?: string;
  dbInfo?: DbInfo;
  error?: string;
};

// Helper function to convert ArrayBuffer to Base64
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return self.btoa(binary);
}

// Helper function to upload file
async function uploadFile(
  token: string,
  fileName: string,
  fileBase64: string
): Promise<{ dbName: string; dbInfo: DbInfo }> {
  const res = await fetch(setupBaseUrl("http", `upload_file_as_db`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      token: token,
      file_name: fileName,
      base_64_file: fileBase64,
    }),
  });

  if (!res.ok) {
    throw new Error(
      "Failed to upload file - are you sure your network is working?"
    );
  }
  const data = await res.json();
  return { dbName: data.db_name, dbInfo: data.db_info };
}

// Set up the event listener for messages from the main thread
self.onmessage = async (event: MessageEvent<WorkerMessageData>) => {
  const { type, token, fileName, fileBuffer } = event.data;

  console.log("Worker event", event.data);

  if (type === "UPLOAD_FILE") {
    try {
      // Convert ArrayBuffer to Base64
      const fileBase64 = arrayBufferToBase64(fileBuffer);

      // Upload the file
      const { dbName, dbInfo } = await uploadFile(token, fileName, fileBase64);

      // Send success response back to main thread
      const response: WorkerResponseData = {
        type: "UPLOAD_SUCCESS",
        dbName,
        dbInfo,
      };
      self.postMessage(response);
    } catch (error) {
      // Send error response back to main thread
      const response: WorkerResponseData = {
        type: "UPLOAD_ERROR",
        error: error instanceof Error ? error.message : String(error),
      };
      self.postMessage(response);
    }
  }
};
