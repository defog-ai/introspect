import setupBaseUrl from "../../utils/setupBaseUrl";
import { DbInfo } from "../../utils/utils";

// Define the message types for communication between the main thread and worker
type WorkerMessageData = {
  type: "UPLOAD_FILE";
  token: string;
  files: File[];
};

type WorkerResponseData = {
  type: "UPLOAD_SUCCESS" | "UPLOAD_ERROR";
  dbName?: string;
  dbInfo?: DbInfo;
  error?: string;
};

/**
 * Uploads multiple files to create a database
 */
export const uploadMultipleFilesAsDb = async (
  token: string,
  files: File[]
): Promise<{ dbName: string; dbInfo: DbInfo }> => {
  const urlToConnect = setupBaseUrl("http", "upload_files");

  const form = new FormData();
  form.append("token", token);
  for (const file of files) {
    form.append("files", file);
  }

  // Use XMLHttpRequest instead of fetch to track upload progress
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.addEventListener("load", async () => {
      console.time("utils:uploadMultipleFilesAsDb:processResponse");

      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          console.timeEnd("utils:uploadMultipleFilesAsDb:processResponse");
          resolve({ dbName: data.db_name, dbInfo: data.db_info });
        } catch (error) {
          reject(new Error("Failed to parse response"));
        }
      } else {
        try {
          // Try to parse the error response as JSON
          const errorData = JSON.parse(xhr.responseText);
          const errorMessage = typeof errorData.detail === 'object' ? 
            JSON.stringify(errorData.detail) : 
            (errorData.detail || errorData.message || "Unknown error occurred");
          reject(new Error(errorMessage));
        } catch {
          // If parsing fails, use the raw response text
          reject(new Error(xhr.responseText || "Failed to create new db name - are you sure your network is working?"));
        }
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Network error occurred"));
    });

    xhr.addEventListener("abort", () => {
      reject(new Error("Upload aborted"));
    });

    xhr.open("POST", urlToConnect);
    xhr.send(form);
  });
};

// Set up the event listener for messages from the main thread
self.onmessage = async (event: MessageEvent<WorkerMessageData>) => {
  const { type, token, files } = event.data;

  console.log("Worker event", event.data);

  if (type === "UPLOAD_FILE") {
    try {
      // Upload the file
      const { dbName, dbInfo } = await uploadMultipleFilesAsDb(token, files);

      // Send success response back to main thread
      const response: WorkerResponseData = {
        type: "UPLOAD_SUCCESS",
        dbName,
        dbInfo,
      };
      self.postMessage(response);
    } catch (error) {
      console.log("Error", error);
      // Send error response back to main thread
      const response: WorkerResponseData = {
        type: "UPLOAD_ERROR",
        error: error instanceof Error ? error.message.replace(/^Error: /, '') : String(error),
      };
      self.postMessage(response);
    }
  }
};
