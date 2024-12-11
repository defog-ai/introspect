"use client";
import React, { useState } from "react";
import "../styles/globals.css";
import "@defogdotai/agents-ui-components/css";
import {
  MessageMonitor,
  MessageManagerContext,
  MessageManager,
} from "@defogdotai/agents-ui-components/core-ui";
import { UserContext } from "$components/context/UserContext";
import { ThemeProvider } from "$components/context/ThemeContext";
import ThemeToggle from "$components/ThemeToggle";
import { ConfigProvider } from "antd";
import { useTheme } from "$components/context/ThemeContext";
import { lightTheme, darkTheme } from "../styles/theme";

console.log("Test action");

function AppContent({ Component, pageProps }) {
  const [context, setContext] = useState({});
  const [darkMode] = useTheme();

  return (
    <ConfigProvider theme={darkMode ? darkTheme : lightTheme}>
      <UserContext.Provider value={[context, setContext]}>
        <MessageManagerContext.Provider value={MessageManager()}>
          <div className="min-h-screen bg-white dark:bg-dark-bg-primary text-primary-text dark:text-dark-text-primary transition-colors">
            <MessageMonitor />
            <Component {...pageProps} />
            <ThemeToggle />
          </div>
        </MessageManagerContext.Provider>
      </UserContext.Provider>
    </ConfigProvider>
  );
}

export default function App(props) {
  return (
    <ThemeProvider>
      <AppContent {...props} />
    </ThemeProvider>
  );
}
