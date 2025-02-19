import { SpinningLoader } from "@defogdotai/agents-ui-components/core-ui";
import { 
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader
} from "lucide-react";
import { useRouter } from "next/router";

const SetupStatus = ({
  loading,
  isDatabaseSetupWell,
  isTablesIndexed,
  hasNonEmptyDescription,
}) => {
  const router = useRouter();

  const statusItems = [
    {
      key: "1",
      title: "Database Setup",
      description: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : isDatabaseSetupWell ? (
        "We can verify that your database details are correct and a connection is successfully established"
      ) : (
        "Please fill in your correct database details to get started querying"
      ),
      status: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : isDatabaseSetupWell ? (
        <CheckCircle className="text-[#96c880] h-5 w-5" />
      ) : (
        <XCircle className="text-[#fc8e8e] h-5 w-5" />
      ),
      onClick: () => router.push("/extract-metadata"),
    },
    {
      key: "2",
      title: "Metadata Setup",
      description: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : isTablesIndexed ? (
        "We can verify that at least one table from your database was indexed for defog to generate queries."
      ) : (
        "We did not find any tables indexed for defog to work on. Please index tables to get started."
      ),
      status: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : isTablesIndexed ? (
        <CheckCircle className="text-[#96c880] h-5 w-5" />
      ) : (
        <AlertCircle className="text-yellow-500 h-5 w-5" />
      ),
      onClick: () => router.push("/extract-metadata"),
      blur: !isDatabaseSetupWell,
    },
    {
      key: "3",
      title: "Column Descriptions",
      description: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : hasNonEmptyDescription ? (
        "We found at least one column with a description. You can view and update metadata."
      ) : (
        "We did not find any column descriptions. Please add descriptions to columns to give defog better context of your data."
      ),
      status: loading ? (
        <Loader className="text-gray-500 dark:text-dark-text-primary h-5 w-5" />
      ) : hasNonEmptyDescription ? (
        <CheckCircle className="text-[#96c880] h-5 w-5" />
      ) : (
        <AlertCircle className="text-yellow-500 h-5 w-5" />
      ),
      onClick: () => router.push("/extract-metadata"),
      blur: !isDatabaseSetupWell,
    },
  ];

  return (
    <div className="py-4">
      <div className="mt-4 flex flex-row gap-4">
        {statusItems.map((item) => (
          <div
            key={item.key}
            className={`w-1/3 ${
              item.blur ? "filter blur-sm pointer-events-none opacity-60" : ""
            }`}
          >
            <div
              className="h-full bg-white dark:bg-dark-bg-secondary border border-gray-200 dark:border-dark-border rounded-lg shadow hover:shadow-md transition-shadow duration-200 cursor-pointer"
              onClick={item.blur ? null : item.onClick}
            >
              <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-border">
                <div className="flex items-center justify-between dark:text-dark-text-primary">
                  <span className="text-base font-medium">{item.title}</span>
                  <span>{item.status}</span>
                </div>
              </div>
              <div className="px-6 py-4">
                <p className="text-gray-600 dark:text-dark-text-secondary text-sm">{item.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SetupStatus;
