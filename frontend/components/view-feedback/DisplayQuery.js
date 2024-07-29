function DisplayQuery({ query }) {
  return (
    <div
      style={{
        backgroundColor: "#f4f4f4",
        padding: "10px",
        borderRadius: "5px",
        fontFamily: "monospace",
      }}
    >
      <pre>{query}</pre>
    </div>
  );
}

export default DisplayQuery;
