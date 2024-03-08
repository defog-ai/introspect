import React, { useState, useEffect, useContext } from "react";
import { Context } from "./Context";
import { Layout, Menu } from "antd/lib";
import { useRouter } from "next/router";

const Scaffolding = ({ id, userType, children }) => {
  const { Content, Sider } = Layout;
  const [items, setItems] = useState([]);
  const [context, setContext] = useContext(Context);

  const router = useRouter();

  const redirect = (path) => {
    router.push(path);
  };

  const logout = () => {
    localStorage.removeItem("defogUser");
    localStorage.removeItem("defogToken");
    localStorage.removeItem("defogUserType");
    setContext({
      user: null,
      token: null,
      userType: null,
    });

    redirect("/log-in");
  };

  useEffect(() => {
    let items = [];
    if (userType == "admin") {
      items = [
        {
          key: "manage-database",
          title: "Manage Database",
          icon: (
            <a onClick={() => redirect("/extract-metadata")}>💾 Manage DB</a>
          ),
        },
        {
          key: "manage-users",
          title: "Manage Users",
          icon: (
            <a onClick={() => redirect("/manage-users")}>🔐 Manage Users</a>
          ),
        },
        {
          key: "view-notebooks",
          title: "View your notebook",
          icon: (
            <a onClick={() => redirect("/view-notebooks")}>📒 Your Notebooks</a>
          ),
        },
        {
          key: "logout",
          title: "Logout",
          icon: <a onClick={logout}>↪ Logout</a>,
        },
      ];
    } else if (!userType) {
      items = [];
    } else {
      items = [
        {
          key: "view-notebooks",
          title: "View your notebook",
          icon: (
            <a onClick={() => redirect("/view-notebooks")}>Your Notebooks</a>
          ),
        },
        {
          key: "logout",
          title: "Logout",
          icon: <a onClick={logout}>Logout</a>,
        },
      ];
    }
    setItems(items);
  }, [userType]);

  return (
    <Layout style={{ height: "100vh" }}>
      <Content>
        {items.length ? (
          <Sider
            style={{
              height: "100vh",
              position: "fixed",
            }}
          >
            <Menu
              style={{ width: 200, paddingTop: "2em", paddingBottom: "2em" }}
              mode="inline"
              selectedKeys={[id]}
              items={items}
            />
          </Sider>
        ) : (
          <></>
        )}
        <div
          style={{
            paddingLeft: 240,
            paddingTop: 30,
            backgroundColor: "#f5f5f5",
          }}
        >
          {children}
        </div>
      </Content>
    </Layout>
  );
};

export default Scaffolding;
