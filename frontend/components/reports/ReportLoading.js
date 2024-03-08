import React, { useEffect } from "react";

export default function LoadingReport({ title = "Getting report" }) {
  useEffect(() => {
    document.title = title;
  }, [title]);

  return /*#__PURE__*/ React.createElement(
    "div",
    {
      style: {
        margin: "0 auto",
        padding: "20px",
        textAlign: "center",
        fontSize: "1.2em",
      },
    },
    /*#__PURE__*/ React.createElement("h5", null, title)
  );
}
