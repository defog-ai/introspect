import React, { useState, useEffect } from "react";
import { useRouter } from "next/router";
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
          title: "Admin",
          href: "#!",
          children: [
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
              key: "evaluate-model",
              title: "Evalute Model",
              href: "/evaluate-model",
            },
          ]
        },
        {
          key: "query-data",
          title: "Query Data",
          href: "/query-data",
        },
        {
          key: "reports",
          title: "Reports",
          href: "/reports",
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
          key: "query-data",
          title: "Query Data",
          href: "/query-data",
        },
        {
          key: "reports",
          title: "Reports",
          href: "/reports",
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

    // do the same for children
    items = items.map((item) => {
      if (item.children) {
        item.children = item.children.map((child) => {
          child.current = child.href == pathname;
          return child;
        });
      }
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
