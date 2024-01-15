import React, { useState, useEffect, useContext } from "react";
import { Context } from "./Context";
import { Layout, Menu } from "antd/lib";

const Scaffolding = ({ id, userType, children }) => {
  const { Content, Sider } = Layout;
  const [items, setItems] = useState([]);
  const [context, setContext] = useContext(Context);
  
  const logout = () => {
    localStorage.removeItem("defogUser");
    localStorage.removeItem("defogToken");
    localStorage.removeItem("defogUserType");
    setContext({
      user: null,
      token: null,
      userType: null,
    });

    window.location.href = "/login";
  }
  
  useEffect(() => {
    let items = [];
    if (userType == "admin") {
      items = [
        {
          key: 'manage-database',
          title: 'Manage Database',
          icon: <a href="/extract-metadata">💾 Manage DB</a>,
        },
        {
          key: 'manage-users',
          title: 'Manage Users',
          icon: <a href="/manage-users">🔐 Manage Users</a>,
        },
        // {
        //   key: 'manage-model',
        //   title: 'Instruct Model',
        //   icon: <a href="/instruct-model">👨‍🏫 Instruct Model</a>,
        // },
        {
          key: 'view-notebook',
          title: 'View your notebook',
          icon: <a href="/view-notebooks">📒 Your Notebooks</a>,
        },
        {
          key: 'logout',
          title: 'Logout',
          icon: <a href="#" onClick={logout}>↪ Logout</a>,
        },
      ];
    } else {
      items = [
        {
          key: 'view-notebook',
          title: 'View your notebook',
          icon: <a href="/view-notebooks">Your Notebooks</a>,
        },
        {
          key: 'logout',
          title: 'Logout',
          icon: <a href="#" onClick={logout}>Logout</a>,
        },
      ]
    }
    setItems(items);
  }, [userType]);

  return (
    <Layout style={{height: "100vh"}}>
      <Content
        style={{
          padding: '50 50',
        }}
      >
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
        <div style={{paddingLeft: 240, paddingTop: 30}}>
          {children}
        </div>
      </Content>
    </Layout>
  );
}

export default Scaffolding;