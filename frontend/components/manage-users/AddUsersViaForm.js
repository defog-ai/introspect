import { useState, useEffect, useContext } from "react";
import { UserPlus, AlertCircle } from "lucide-react";
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
  const [validationErrors, setValidationErrors] = useState([]);
  const message = useContext(MessageManagerContext);

  const getApiKeyNames = async () => {
    const token = localStorage.getItem("defogToken");
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_db_names",
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
    setAllowedDbs(data.db_names);
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

  const validateEmail = (email) => {
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return emailRegex.test(email);
  };

  const validatePassword = (password) => {
    if (!password) return true; // Empty password is allowed for SSO users
    if (password.length < 8) return false;

    const hasUppercase = /[A-Z]/.test(password);
    const hasLowercase = /[a-z]/.test(password);
    const hasDigit = /\d/.test(password);
    const hasSpecial = /[^A-Za-z0-9]/.test(password);

    return hasUppercase && hasLowercase && hasDigit && hasSpecial;
  };

  const handleChange = (index, field, value) => {
    const newUsers = [...users];
    newUsers[index][field] = value;
    setUsers(newUsers);
    
    // Validate as user types
    validateUsers(newUsers);
  };

  const validateUsers = (usersList) => {
    const errors = [];
    
    usersList.forEach((user, idx) => {
      // Validate email
      if (user.username && !validateEmail(user.username)) {
        errors.push(`User ${idx + 1}: Invalid email format for username`);
      }
      
      // Validate password if provided
      if (user.password && !validatePassword(user.password)) {
        errors.push(
          `User ${idx + 1}: Password must be at least 8 characters with uppercase, lowercase, number, and special character`
        );
      }
    });
    
    setValidationErrors(errors);
    return errors.length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Final validation before submission
    if (!validateUsers(users)) {
      message.error("Please fix validation errors before submitting");
      return;
    }
    
    const token = localStorage.getItem("defogToken");
    
    try {
      const res = await fetch(setupBaseUrl("http", `admin/add_users`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ users_csv: csvString, token: token }),
      });
      
      const data = await res.json();
      
      if (data.status === "success") {
        message.success(data.message || "Users added successfully! Refreshing the user data...");
        setUsers([{ username: "", password: "", userType: "", userDb: [] }]); // Clear the form values
        setValidationErrors([]);
      } else {
        if (data.detail && Array.isArray(data.detail)) {
          // Display specific validation errors from backend
          setValidationErrors(data.detail);
          message.error("There were errors with the submitted users. Please fix them and try again.");
        } else {
          message.error(data.message || "There was an error adding the users. Please try again.");
        }
      }
    } catch (error) {
      console.error(error);
      message.error("An unexpected error occurred. Please try again.");
    }
    
    await getUserDets();
  };

  const removeUser = (index) => {
    if (users.length === 1) {
      // Reset the first user instead of removing it
      setUsers([{ username: "", password: "", userType: "", userDb: [] }]);
    } else {
      const newUsers = users.filter((_, idx) => idx !== index);
      setUsers(newUsers);
    }
  };

  const addUser = () => {
    setUsers([...users, { username: "", password: "", userType: "", userDb: [] }]);
  };

  return (
    <div className="w-3/4 p-6 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg bg-white dark:bg-gray-800">
      <h1 className="flex items-center justify-center text-2xl mb-8 dark:text-gray-100">
        <UserPlus size={24} className="mr-2 dark:text-blue-400" />
        Add Users Manually
      </h1>

      {validationErrors.length > 0 && (
        <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <div className="flex items-center text-red-600 dark:text-red-400 font-medium mb-2">
            <AlertCircle size={18} className="mr-2" />
            Please fix the following errors:
          </div>
          <ul className="list-disc list-inside text-sm text-red-600 dark:text-red-400">
            {validationErrors.map((error, idx) => (
              <li key={idx}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      <form onSubmit={handleSubmit} className="w-full space-y-6">
        {users.map((user, index) => (
          <div key={index} className="p-4 border border-gray-200 dark:border-gray-700 rounded-md bg-gray-50 dark:bg-gray-800">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-md font-medium dark:text-gray-200">
                User {index + 1}
              </h3>
              <button
                type="button"
                onClick={() => removeUser(index)}
                className="text-red-500 hover:text-red-700 text-sm"
                disabled={loading}
              >
                Remove
              </button>
            </div>
            
            <div className="flex flex-wrap -mx-2">
              <div className="w-1/2 px-2 mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Email Address<span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 dark:bg-gray-700 dark:text-gray-200"
                  value={user.username}
                  onChange={(e) =>
                    handleChange(index, "username", e.target.value)
                  }
                  required
                  disabled={loading}
                  placeholder="user@example.com"
                />
                {user.username && !validateEmail(user.username) && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    Please enter a valid email address
                  </p>
                )}
              </div>

              <div className="w-1/2 px-2 mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Password (leave blank for SSO users)
                </label>
                <input
                  type="password"
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 dark:bg-gray-700 dark:text-gray-200"
                  value={user.password}
                  onChange={(e) =>
                    handleChange(index, "password", e.target.value)
                  }
                  disabled={loading}
                />
                {user.password && !validatePassword(user.password) && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    Password must be at least 8 characters with uppercase, lowercase, digit, and special character
                  </p>
                )}
                {!user.password && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    For SSO users, leave this field blank
                  </p>
                )}
              </div>

              <div className="w-1/2 px-2 mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  User Type<span className="text-red-500">*</span>
                </label>
                <select
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 dark:bg-gray-700 dark:text-gray-200"
                  value={user.userType}
                  onChange={(e) =>
                    handleChange(index, "userType", e.target.value)
                  }
                  required
                  disabled={loading}
                >
                  <option value="">Select type</option>
                  <option value="ADMIN">Admin</option>
                  <option value="GENERAL">General</option>
                </select>
              </div>

            </div>
          </div>
        ))}

        <button
          type="button"
          onClick={addUser}
          className="w-full py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 dark:focus:ring-gray-400"
          disabled={loading}
        >
          Add Another User
        </button>

        {csvString.trim() !== "username,password,user_type,allowed_dbs" && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Generated CSV String
            </label>
            <textarea
              value={csvString}
              readOnly
              rows={2}
              className="w-full font-mono border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-gray-100 dark:bg-gray-700 dark:text-gray-200 p-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
        )}

        <button
          type="submit"
          className="w-1/3 mx-auto block mt-10 py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={
            loading ||
            csvString.trim() === "username,password,user_type,allowed_dbs" ||
            validationErrors.length > 0
          }
        >
          Add Users
        </button>
      </form>
    </div>
  );
};

export default AddUsersViaForm;
