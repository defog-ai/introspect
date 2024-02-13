import { createContext } from "react";

export const DocContext = createContext({
  userItems: {
    analyses: [],
    toolboxes: [],
    metadata: {},
  },
  dbCreds: {
    dbType: "postgres",
    host: "",
    port: "",
    user: "",
    password: "",
    database: "",
    hasCreds: false,
  },
  recipeShowing: null,
});

export const ToolRunContext = createContext({
  toolRunData: {},
});

export const RelatedAnalysesContext = createContext({});
