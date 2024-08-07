function DisplayData({ columns, data }) {
  return (
    <div className="max-w-full max-h-screen overflow-auto"> 
      <table className="min-w-full border-collapse">
        <thead>
          <tr>
            {columns.map((col, index) => (
              <th
                key={index}
                className="border px-8 py-2 bg-gray-200 text-center"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className="border px-8 py-2 text-center"
                >
                  {cell.toString()}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DisplayData;
