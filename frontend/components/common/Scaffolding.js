import React, { useState, useEffect, useContext } from "react";
import { Context } from "./Context";
import { Layout } from "antd/lib";
import { useRouter } from "next/router";
import Link from "next/link";
import { NavBar } from "$ui-components";
import { usePathname } from "next/navigation";

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

  const pathname = usePathname();

  useEffect(() => {
    let items = [];
    if (userType == "admin") {
      items = [
        {
          key: "manage-database",
          title: "Manage Database",
          href: "/extract-metadata",
        },
        {
          key: "manage-users",
          title: "Manage Users",
          href: "/manage-users",
        },
        {
          key: "view-notebooks",
          title: "View your notebook",
          href: "/view-notebooks",
        },
        {
          key: "manage-tools",
          title: "Manage tools",
          href: "/manage-tools",
        },
        {
          key: "check-readiness",
          title: "Check Readiness",
          href: "/check-readiness",
        },
        {
          key: "align-model",
          title: "Align Model",
          href: "/align-model",
        },
        {
          key: "query-data",
          title: "Query Data",
          href: "/query-data",
        },
        {
          key: "logout",
          classNames: "self-end",
          title: "Logout",
          href: "#",
          onClick: logout,
        },
      ];
    } else if (!userType) {
      items = [];
    } else {
      items = [
        {
          key: "view-notebooks",
          title: "View your notebook",
          href: "/view-notebooks",
        },
        {
          key: "query-data",
          title: "Query Data",
          href: "/query-data",
        },
        {
          key: "logout",
          classNames: "self-end",
          title: "Logout",
          href: "#",
          onClick: logout,
        },
      ];
    }

    // set the item's current to true if it matches pathname
    items = items.map((item) => {
      item.current = item.href == pathname;
      return item;
    });

    setItems(items);
  }, [userType]);

  return (
    <div className="flex flex-col md:min-h-screen relative">
      {items.length ? (
        <NavBar rootClassNames="border-b" items={items}></NavBar>
      ) : (
        <></>
      )}
      <div className="grow">{children}</div>
    </div>
  );
};

export default Scaffolding;
