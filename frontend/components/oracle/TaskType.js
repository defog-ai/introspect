import {
  SearchOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { Tag } from "antd";

export default function TaskType({ taskType }) {
  if (taskType === "exploration") {
    return (
      <div className="flex items-center my-2">
        <h4 className="text-l font-semibold pr-4">Task Type</h4>
        <div className="inline-flex items-center w-max h-10 gap-2.5 border border-gray-300 rounded-md">
          <SearchOutlined className="text-[#1B1B16]/30 ml-2" />
          <h6 className="mr-2">Exploration</h6>
        </div>
      </div>
    );
  }
  if (taskType === "prediction") {
    return (
      <div className="flex items-center my-2">
        <h4 className="text-l font-semibold pr-4">Task Type</h4>
        <div className="inline-flex items-center w-max h-10 gap-2.5 border border-gray-300 rounded-md">
          <LineChartOutlined className="text-[#1B1B16]/30 ml-2" />
          <h6 className="mr-2">Prediction</h6>
        </div>
      </div>
    );
  }
  if (taskType === "optimization") {
    return (
      <div className="flex items-center my-2">
        <h4 className="text-l font-semibold pr-4">Task Type</h4>
        <div className="inline-flex items-center w-max h-10 gap-2.5 border border-gray-300 rounded-md">
          <ThunderboltOutlined className="text-[#1B1B16]/30 ml-2" />
          <h6 className="mr-2">Optimization</h6>
        </div>
      </div>
    );
  }
  return null;
}
