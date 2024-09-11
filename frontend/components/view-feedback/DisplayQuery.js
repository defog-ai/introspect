function DisplayQuery({ query }) {
  return (
    <div className="bg-gray-100 p-4 rounded-md font-mono max-h-48 overflow-auto">
      <pre>{query}</pre>
    </div>
  );
}

export default DisplayQuery;
