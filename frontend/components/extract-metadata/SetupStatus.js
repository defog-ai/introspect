import { Card, Row, Col } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
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
        <LoadingOutlined className="dark:text-dark-text-primary" />
      ) : isDatabaseSetupWell ? (
        "We can verify that your database details are correct and a connection is successfully established"
      ) : (
        "Please fill in your correct database details to get started querying"
      ),
      status: loading ? (
        <LoadingOutlined className="dark:text-dark-text-primary" />
      ) : isDatabaseSetupWell ? (
        <CheckCircleOutlined style={{ color: "#96c880" }} />
      ) : (
        <CloseCircleOutlined style={{ color: "#fc8e8e" }} />
      ),
      onClick: () => router.push("/extract-metadata"),
    },
    {
      key: "2",
      title: "Metadata Setup",
      description: loading ? (
        <LoadingOutlined className="dark:text-dark-text-primary" />
      ) : isTablesIndexed ? (
        "We can verify that at least one table from your database was indexed for defog to generate queries."
      ) : (
        "We did not find any tables indexed for defog to work on. Please index tables to get started."
      ),
      status: loading ? (
        <LoadingOutlined className="dark:text-dark-text-primary" />
      ) : isTablesIndexed ? (
        <CheckCircleOutlined style={{ color: "#96c880" }} />
      ) : (
        <CloseCircleOutlined style={{ color: "#fc8e8e" }} />
      ),
      onClick: () => router.push("/extract-metadata"),
      blur: !isDatabaseSetupWell, // Add blur property
    },
    {
      key: "3",
      title: "Column Descriptions",
      description: loading ? (
        <LoadingOutlined className="dark:text-dark-text-primary" />
      ) : hasNonEmptyDescription ? (
        "We found at least one column with a description. You can view and update metadata."
      ) : (
        "We did not find any column descriptions. Please add descriptions to columns to give defog better context of your data."
      ),
      status: loading ? (
        <LoadingOutlined className="dark:text-dark-text-primary" />
      ) : hasNonEmptyDescription ? (
        <CheckCircleOutlined style={{ color: "#96c880" }} />
      ) : (
        <CloseCircleOutlined style={{ color: "#fc8e8e" }} />
      ),
      onClick: () => router.push("/extract-metadata"),
      blur: !isDatabaseSetupWell, // Add blur property
    },
  ];

  return (
    <div className="py-4">
      <Row gutter={[16, 16]} className="mt-4">
        {statusItems.map((item) => (
          <Col key={item.key} xs={24} sm={24} md={8}>
            <div
              className={`${
                item.blur ? "filter blur-sm pointer-events-none opacity-60" : ""
              }`}
            >
              <Card
                title={
                  <div className="flex items-center justify-between dark:text-dark-text-primary">
                    <span>{item.title}</span>
                    <span>{item.status}</span>
                  </div>
                }
                className="h-full cursor-pointer hover:shadow-lg transition-shadow duration-200 dark:bg-dark-bg-secondary dark:border-dark-border"
                onClick={item.blur ? null : item.onClick}
              >
                <p className="dark:text-dark-text-secondary">{item.description}</p>
              </Card>
            </div>
          </Col>
        ))}
      </Row>
    </div>
  );
};

export default SetupStatus;
