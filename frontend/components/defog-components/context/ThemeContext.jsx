import React, { createContext, useEffect, useState } from "react";

export const ThemeContext = createContext({});

export const lightThemeColor = {
  primaryText: "#0D0D0D",
  secondaryText: "#161616",
  brandColor: "#2B59FF",
  background1: "#FFFFFF",
  background2: "#F8FAFB",
  background3: "#F8FAFB",
  disabledColor: "#f5f5f5",
  greyBorder: "#EFF1F5",
  questionBorder: "#EFF1F5",
  answerBorder: "#EFF1F5",
};

export const darkThemeColor = {
  primaryText: "#FFFFFF",
  secondaryText: "#606060",
  hightlightText: "#2B59FF",
  brandColor: "#2B59FF",
  background1: "#070710",
  background2: "#131321",
  background3: "#0C0C1E",
  disabledColor: "#202020",
  greyBorder: "#3C3C40",
  questionBorder: "#3D3D4B",
  answerBorder: "#2B59FF",
};

export const chartColors = [
  "#D52D68",
  "#540CC9",
  "#2B59FF",
  "#FFB536",
  "#3EE0D5",
  "#561981",
];

const ThemeContextProvider = ({ children }) => {
  const [theme, setTheme] = useState({
    type: "light",
    config: darkThemeColor,
  });

  useEffect(() => {
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)")
      .matches
      ? "dark"
      : "light";

    if (systemTheme === "dark") {
      setTheme({ type: "dark", config: darkThemeColor });
    } else {
      setTheme({ type: "light", config: lightThemeColor });
    }
  }, []);

  const toggleTheme = () => {
    setTheme(
      theme.type === "light"
        ? { type: "dark", config: darkThemeColor }
        : { type: "light", config: lightThemeColor }
    );
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export default ThemeContextProvider;
