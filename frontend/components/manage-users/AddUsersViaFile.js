import React, { useState, useEffect, useContext } from "react";
import { FileUp, Upload } from "lucide-react";
import setupBaseUrl from "$utils/setupBaseUrl";
import Papa from "papaparse";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";

const AddUsersViaFile = ({ loading, getUserDets }) => {
  const [users, setUsers] = useState([
    { username: "", password: "", userType: "" },
  ]);
  const [csvString, setCsvString] = useState("username,password,user_type\n");
  const [googleSheetsUrl, setGoogleSheetsUrl] = useState("");
  const [isFileUploaded, setFileUploaded] = useState(false);
  const message = useContext(MessageManagerContext);
  const fileInputRef = React.useRef(null);

  useEffect(() => {
    const csv = users
      .filter((user) => user.username && user.password && user.userType)
      .map((user) => `${user.username},${user.password},${user.userType}`)
      .join("\n");
    setCsvString(`username,password,user_type\n${csv}`);
  }, [users]);

  const handleFileUpload = (file) => {
    Papa.parse(file, {
      error: (error) => {
        message.error("There was an error parsing the CSV file.");
      },
      complete: (results) => {
        const parsedData = results.data.map((row) => ({
          username: row.username,
          password: row.password,
          userType: row.user_type,
        }));
        setUsers(parsedData);
        setFileUploaded(true);
        setGoogleSheetsUrl("");
        message.success(
          "CSV file parsed successfully. Please hit 'Add Users' to proceed."
        );
      },
      header: true,
      skipEmptyLines: true,
    });
    return false;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const endpoint = "admin/add_users";
      const token = localStorage.getItem("defogToken");

      const payload =
        csvString.trim() !== "username,password,user_type"
          ? { users_csv: csvString, token: token }
          : { gsheets_url: googleSheetsUrl, token: token };

      const res = await fetch(setupBaseUrl("http", endpoint), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();

      if (data.status === "success") {
        message.success(
          "Users added successfully! Refreshing the user data..."
        );
        setUsers([{ username: "", password: "", userType: "" }]);
      } else {
        throw new Error(data.message || "There was an error adding the users.");
      }
      await getUserDets();
    } catch (error) {
      console.error("Error:", error);
      message.error(
        error.message ||
          "There was an error adding the users. Please try again."
      );
    } finally {
      setFileUploaded(false);
      setCsvString("username,password,user_type\n");
    }
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  return (
    <div className="w-3/4 p-6 border border-gray-200 rounded-lg shadow-lg">
      <h1 className="flex items-center justify-center text-2xl mb-8">
        <FileUp size={24} className="mr-2" />
        Add Users via File
      </h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <h4 className="text-lg font-semibold mb-4">Upload CSV File</h4>
          <div className="mb-4">
            {!isFileUploaded && (
              <p className="text-sm text-gray-600 mb-2">
                Expected columns in the file: username,password,user_type,allowed_dbs. For users that must login via SSO, please set the password column to blank.
              </p>
            )}
            <input
              type="file"
              ref={fileInputRef}
              accept=".csv"
              onChange={handleFileInputChange}
              className="hidden"
              disabled={isFileUploaded || loading}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isFileUploaded || loading}
              className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Upload size={20} className="mr-2" />
              {isFileUploaded ? "Uploaded" : "Upload CSV"}
            </button>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-4">
            Or a paste publicly accessible Google Sheets URL
          </h4>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700">
              Google Sheets URL
            </label>
            <input
              type="text"
              value={googleSheetsUrl}
              onChange={(e) => setGoogleSheetsUrl(e.target.value)}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              disabled={loading}
            />
          </div>
        </div>

        {isFileUploaded && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700">
              Generated CSV String
            </label>
            <textarea
              value={csvString}
              readOnly
              rows={4}
              className="mt-1 block w-full font-mono border border-gray-300 rounded-md shadow-sm py-2 px-3 bg-gray-100 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
        )}

        <button
          type="submit"
          disabled={csvString.trim() === "username,password,user_type" && !googleSheetsUrl || loading}
          className="w-1/3 mx-auto block px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add Users
        </button>
      </form>
    </div>
  );
};

export default AddUsersViaFile;
