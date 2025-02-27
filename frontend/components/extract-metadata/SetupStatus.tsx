import { CheckCircle, XCircle, AlertCircle, Loader } from "lucide-react";
import { useRouter } from "next/router";

const SetupStatus = ({
  loading,
  canConnect,
  areTablesIndexed,
  hasNonEmptyDescription,
}) => {
  const statusItems = [
    {
      key: "1",
      title: "Database Setup",
      description: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : canConnect ? (
        "Database connection verified"
      ) : (
        "We could not connect to your database. Please check your connection details."
      ),
      status: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : canConnect ? (
        <CheckCircle className="text-[#96c880] h-5 w-5" />
      ) : (
        <XCircle className="text-[#fc8e8e] h-5 w-5" />
      ),
    },
    {
      key: "2",
      title: "Metadata Setup",
      description: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : areTablesIndexed ? (
        "AI metadata generated for at least one table"
      ) : (
        "AI metadata not generated. Queries will be incorrect."
      ),
      status: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : areTablesIndexed ? (
        <CheckCircle className="text-[#96c880] h-5 w-5" />
      ) : (
        <AlertCircle className="text-yellow-500 h-5 w-5" />
      ),
      blur: !canConnect,
    },
    {
      key: "3",
      title: "Column Descriptions",
      description: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : hasNonEmptyDescription ? (
        "We found at least one column with a description. You can view and update the metadata."
      ) : (
        "We did not find any column descriptions. Queries will be incorrect."
      ),
      status: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : hasNonEmptyDescription ? (
        <CheckCircle className="text-[#96c880] h-5 w-5" />
      ) : (
        <AlertCircle className="text-yellow-500 h-5 w-5" />
      ),
      blur: !canConnect,
    },
  ];

  return (
    <div className="mt-4 flex flex-row gap-4">
      {statusItems.map((item) => (
        <div
          key={item.key}
          className={`w-1/3 ${
            item.blur ? "filter blur-sm pointer-events-none opacity-60" : ""
          }`}
        >
          <div className="h-full bg-white dark:bg-dark-bg-secondary border border-gray-200 dark:border-dark-border rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-border">
              <div className="flex items-center justify-between dark:text-dark-text-primary">
                <span className="text-base font-medium">{item.title}</span>
                <span>{item.status}</span>
              </div>
            </div>
            <div className="px-6 py-4">
              <p className="text-gray-600 dark:text-dark-text-secondary text-sm">
                {item.description}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default SetupStatus;
