import { useState, useEffect, useContext } from "react";
import { IdcardOutlined } from "@ant-design/icons";
import setupBaseUrl from "$utils/setupBaseUrl";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";

const AddUsersViaForm = ({ loading, getUserDets }) => {
  const [users, setUsers] = useState([
    { username: "", password: "", userType: "", userDb: [] },
  ]);
  const [csvString, setCsvString] = useState(
    "username,password,user_type,allowed_dbs\n"
  );
  const [allowedDbs, setAllowedDbs] = useState([]);
  const message = useContext(MessageManagerContext);

  const getApiKeyNames = async () => {
    const token = localStorage.getItem("defogToken");
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_api_key_names",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
        }),
      }
    );
    if (!res.ok) {
      throw new Error(
        "Failed to get api key names - are you sure your network is working?"
      );
    }
    const data = await res.json();
    setAllowedDbs(data.api_key_names);
  };

  useEffect(() => {
    getApiKeyNames();
    const csv = users
      .filter((user) => user.username && user.userType)
      .map(
        (user) =>
          `${user.username},${user.password || ""},${
            user.userType
          },${user.userDb.join("|")}`
      )
      .join("\n");
    setCsvString(`username,password,user_type,allowed_dbs\n${csv}`);
  }, [users]);

  const handleChange = (index, field, value) => {
    const newUsers = [...users];
    newUsers[index][field] = value;
    setUsers(newUsers);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("defogToken");
    const res = await fetch(setupBaseUrl("http", `admin/add_users`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ users_csv: csvString, token: token }),
    });
    const data = await res.json();
    if (data.status === "success") {
      message.success("Users added successfully! Refreshing the user data...");
      setUsers([{ username: "", password: "", userType: "", userDb: [] }]); // Clear the form values
    } else {
      message.error("There was an error adding the users. Please try again.");
    }
    await getUserDets();
  };

  return (
    <div className="w-3/4 p-6 border border-gray-200 rounded-lg shadow-lg">
      <h1 className="text-center text-2xl mb-8">
        <IdcardOutlined className="mr-2" />
        Add Users Manually
      </h1>

      <form onSubmit={handleSubmit} className="w-full space-y-6">
        {users.map((user, index) => (
          <div key={index} className="flex space-x-4 mb-4">
            <div className="w-1/4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username<span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                className="w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2"
                value={user.username}
                onChange={(e) =>
                  handleChange(index, "username", e.target.value)
                }
                required
                disabled={loading}
              />
            </div>

            <div className="w-1/4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password (leave blank for SSO users)
              </label>
              <input
                type="password"
                className="w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2"
                value={user.password}
                onChange={(e) =>
                  handleChange(index, "password", e.target.value)
                }
                disabled={loading}
              />
            </div>

            <div className="w-1/4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                User Type<span className="text-red-500">*</span>
              </label>
              <select
                className="w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2"
                value={user.userType}
                onChange={(e) =>
                  handleChange(index, "userType", e.target.value)
                }
                required
                disabled={loading}
              >
                <option value="">Select type</option>
                <option value="admin">Admin</option>
                <option value="general">General</option>
              </select>
            </div>

            <div className="w-1/4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Allowed DBs (leave blank for all DBs)
              </label>
              <select
                multiple
                className="w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2"
                value={user.userDb}
                onChange={(e) =>
                  handleChange(
                    index,
                    "userDb",
                    Array.from(
                      e.target.selectedOptions,
                      (option) => option.value
                    )
                  )
                }
                disabled={loading}
              >
                {allowedDbs.map((db) => (
                  <option key={db} value={db}>
                    {db}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))}

        <button
          type="button"
          onClick={() =>
            setUsers([
              ...users,
              { username: "", password: "", userType: "", userDb: [] },
            ])
          }
          className="w-full py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-gray-700 bg-gray-100 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
          disabled={loading}
        >
          Add Another User
        </button>

        {csvString.trim() !== "username,password,user_type,allowed_dbs" && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Generated CSV String
            </label>
            <textarea
              value={csvString}
              readOnly
              rows={2}
              className="w-full font-mono border border-gray-300 rounded-md shadow-sm bg-gray-100 p-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
        )}

        <button
          type="submit"
          className="w-1/3 mx-auto block mt-20 py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={
            loading ||
            csvString.trim() === "username,password,user_type,allowed_dbs"
          }
        >
          Add Users
        </button>
      </form>
    </div>
  );
};

export default AddUsersViaForm;
