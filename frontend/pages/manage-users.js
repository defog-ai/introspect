import { useState, useEffect, useContext } from "react";
import { useRouter } from "next/router";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import setupBaseUrl from "$utils/setupBaseUrl";
import AddUsersViaFile from "components/manage-users/AddUsersViaFile";
import AddUsersViaForm from "components/manage-users/AddUsersViaForm";
import UsersTable from "components/manage-users/UsersTable";
import { TeamOutlined } from "@ant-design/icons";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";

const ManageUsers = () => {
  const [loading, setLoading] = useState(false);
  const [userDets, setUserDets] = useState([]);
  const message = useContext(MessageManagerContext);

  const router = useRouter();

  const getUserDets = async () => {
    setLoading(true);
    const token = localStorage.getItem("defogToken");
    if (!token) {
      setLoading(false);
      message.error(
        "It seems like there was no token found in your session. Please try to log in again."
      );
      return;
    }

    const res = await fetch(setupBaseUrl("http", "admin/get_users"), {
      method: "POST",
      body: JSON.stringify({ token: token }),
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
      getUserDets();
    }
  }, []);

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
            getUserDets={getUserDets}
            loading={loading}
            setLoading={setLoading}
          />
        </div>
        <div className="flex justify-center items-center flex-col p-1 w-full">
          <AddUsersViaFile loading={loading} getUserDets={getUserDets} />
        </div>
        <div className="flex justify-center items-center flex-col p-1 w-full mt-4 mb-4">
          <AddUsersViaForm loading={loading} getUserDets={getUserDets} />
        </div>
      </Scaffolding>
    </>
  );
};

export default ManageUsers;
