import { useState, useEffect, useContext } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import { UserContext } from "$components/context/UserContext";
import setupBaseUrl from "$utils/setupBaseUrl";
import AddUsersForm from "components/manage-users/AddUsersForm";
import AddUsersCSVForm from "components/manage-users/AddUsersCSVForm";
import UsersTable from "components/manage-users/UsersTable";
import { message } from "antd";
import { TeamOutlined } from "@ant-design/icons";

const ManageUsers = () => {
  const [loading, setLoading] = useState(false);
  const [userDets, setUserDets] = useState([]);
  const [context, setContext] = useContext(UserContext);

  const router = useRouter();

  const getUserDets = async () => {
    if (!context.token) {
      return;
    }

    const res = await fetch(setupBaseUrl("http", "admin/get_users"), {
      method: "POST",
      body: JSON.stringify({ token: context.token }),
      headers: { "Content-Type": "application/json" },
    });
    const data = await res.json();
    if (data.users) {
      setUserDets(data.users);
    } else {
      message.error(
        "There was an error fetching the user data. Please try again."
      );
    }
  };

  useEffect(() => {
    let token = context.token;
    let userType = context.userType;
    if (!userType) {
      // load from local storage and set context
      const user = localStorage.getItem("defogUser");
      token = localStorage.getItem("defogToken");
      userType = localStorage.getItem("defogUserType");

      if (!user || !token || !userType) {
        // redirect to login page
        router.push("/log-in");
        return;
      }
      setContext({
        user: user,
        token: token,
        userType: userType,
      });
    }
    if (!token) {
      router.push("/log-in");
    } else {
      getUserDets();
    }
  }, [context, context.token]);

  return (
    <>
      <Meta />
      <Scaffolding id={"manage-users"} userType={"admin"}>
        <div className="flex justify-center items-center flex-col p-1 mt-5">
          <h1>
            <TeamOutlined style={{ fontSize: "3.5em", color: "#1890ff" }} />{" "}
          </h1>
          <h1 className="text-3xl mt-4">Manage Users</h1>
        </div>
        <div className="flex justify-center items-center flex-col p-1">
          <UsersTable
            userDets={userDets}
            context={context}
            getUserDets={getUserDets}
            setLoading={setLoading}
          />
        </div>
        <div className="flex justify-center items-center flex-col p-1 w-full">
          <AddUsersForm
            loading={loading}
            context={context}
            getUserDets={getUserDets}
            setLoading={setLoading}
          />
        </div>
        <div className="flex justify-center items-center flex-col p-1 w-full mt-4 mb-4">
          <AddUsersCSVForm
            loading={loading}
            context={context}
            getUserDets={getUserDets}
            setLoading={setLoading}
          />
        </div>
      </Scaffolding>
    </>
  );
};

export default ManageUsers;
