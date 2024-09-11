import { useState } from 'react';

function DisplayData({ columns, data }) {
  const [currentPage, setCurrentPage] = useState(1);  // Current page
  const rowsPerPage = 4;  // Rows to display per page

  // Calculate total number of pages
  const totalPages = Math.ceil(data.length / rowsPerPage);

  // Get current data based on the current page
  const indexOfLastRow = currentPage * rowsPerPage;
  const indexOfFirstRow = indexOfLastRow - rowsPerPage;
  const currentData = data.slice(indexOfFirstRow, indexOfLastRow);

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  return (
    <div>
      <div className="max-w-full max-h-60 overflow-auto"> 
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
            {currentData.map((row, rowIndex) => (
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

      {/* Pagination Controls */}
      <div className="flex justify-center mt-4 space-x-4">
        <button
          onClick={handlePrevPage}
          className="px-4 py-2 bg-gray-300 rounded"
          disabled={currentPage === 1}
        >
          {/* Left Arrow */}
          &lt;
        </button>
        <span className="px-4 py-2">
          Page {currentPage} of {totalPages}
        </span>
        <button
          onClick={handleNextPage}
          className="px-4 py-2 bg-gray-300 rounded"
          disabled={currentPage === totalPages}
        >
          {/* Right Arrow */}
          &gt;
        </button>
      </div>
    </div>
  );
}

export default DisplayData;
