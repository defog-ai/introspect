import React, { useState, useEffect, useContext } from "react";
import { UserContext } from "../context/UserContext";
import { useRouter } from "next/router";
import Link from "next/link";
import { NavBar } from "@defogdotai/agents-ui-components/core-ui";
import { usePathname } from "next/navigation";
import { twMerge } from "tailwind-merge";
import { useTheme } from "../context/ThemeContext";

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
  const [darkMode] = useTheme();

  const router = useRouter();

  const redirect = (path) => {
    router.push(path);
  };

  const logout = () => {
    localStorage.removeItem("defogUser");
    localStorage.removeItem("defogToken");
    localStorage.removeItem("defogUserType");

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
        // {
        //   key: "manage-tools",
        //   title: "Manage tools",
        //   href: "/manage-tools",
        // },
        {
          key: "test-regression",
          title: "Test Regression",
          href: "/test-regression",
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
        <NavBar
          rootClassNames={twMerge(
            "border-b dark:border-dark-border",
            "bg-white dark:bg-dark-bg-primary",
            "text-primary-text dark:text-dark-text-primary"
          )}
          items={items.map((item) => ({
            ...item,
            classNames: twMerge(
              item.classNames,
              "hover:bg-gray-100 dark:hover:bg-dark-hover",
              item.current && "bg-gray-100 dark:bg-dark-hover"
            ),
          }))}
        />
      ) : (
        <></>
      )}
      <div className={contentClassNames}>{children}</div>
    </div>
  );
};

export default Scaffolding;
