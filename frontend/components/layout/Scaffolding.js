import React, { useState, useEffect, useContext } from "react";
import { UserContext } from "../context/UserContext";
import { useRouter } from "next/router";
import Link from "next/link";
import { NavBar } from "@defogdotai/agents-ui-components/core-ui";
import { usePathname } from "next/navigation";
import { twMerge } from "tailwind-merge";

const Scaffolding = ({
  id,
  userType,
  children,
  rootClassNames = "",
  contentClassNames = "max-h-full h-full",
  containerClassNames = "flex flex-col md:min-h-screen relative container mx-auto",
}) => {
  const [items, setItems] = useState([]);
  const [context, setContext] = useContext(UserContext);

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
        // {
        //   key: "view-notebooks",
        //   title: "View your notebook",
        //   href: "/view-notebooks",
        // },
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
          key: "view-feedback",
          title: "View Feedback",
          href: "/view-feedback",
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
        // {
        //   key: "view-notebooks",
        //   title: "View your notebook",
        //   href: "/view-notebooks",
        // },
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
    <div className={twMerge(containerClassNames, rootClassNames)}>
      {items.length ? (
        <NavBar rootClassNames="border-b" items={items}></NavBar>
      ) : (
        <></>
      )}
      <div className={contentClassNames}>{children}</div>
    </div>
  );
};

export default Scaffolding;
