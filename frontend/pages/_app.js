import React, { useState } from "react";
import '../styles/globals.css';
import "$agents-ui-styles";
import {
  MessageMonitor,
  MessageManagerContext,
  MessageManager,
} from "$ui-components";
import { UserContext } from "$components/context/UserContext";

export default function App({ Component, pageProps }) {
  const [context, setContext] = useState({});

  return (
    <UserContext.Provider value={[context, setContext]}>
      <MessageManagerContext.Provider value={MessageManager()}>
        <MessageMonitor />
        <Component {...pageProps} />
      </MessageManagerContext.Provider>
    </UserContext.Provider>
  );
}
