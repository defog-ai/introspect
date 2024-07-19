const setupBaseUrl = (protocol, path) => {
  if (protocol !== "http" && protocol !== "ws") {
    throw new Error("Protocol not supported");
  }

  console.log(process.env.NEXT_PUBLIC_AGENTS_ENDPOINT);

  if (path !== "") {
    if (protocol === "ws") {
      return `${(process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "").replace(
        "http",
        "ws"
      )}/${path}`;
    } else {
      return `${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}/${path}`;
    }
  }

  return `${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}`;
};

export default setupBaseUrl;
