const setupBaseUrl = (protocol, path) => {
  if (protocol !== "http" && protocol !== "ws") {
    throw new Error("Protocol not supported");
  }
  let urlToConnect;
  if (path !== "")
    urlToConnect = `${protocol}://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/${path}`;
  else
    urlToConnect = `${protocol}://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}`;

  return urlToConnect;
};

export default setupBaseUrl;
