import { Select } from "antd";
import {
  SearchOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

const taskOptions = [
  {
    value: "exploration",
    label: (
      <span>
        <SearchOutlined className="text-[#1B1B16]/30 ml-2" /> Exploration
      </span>
    ),
  },
  // {
  //   value: "prediction",
  //   label: (
  //     <span>
  //       <LineChartOutlined className="text-[#1B1B16]/30 ml-2" /> Prediction
  //     </span>
  //   ),
  // },
  // {
  //   value: "optimization",
  //   label: (
  //     <span>
  //       <ThunderboltOutlined className="text-[#1B1B16]/30 ml-2" /> Optimization
  //     </span>
  //   ),
  // },
];

export default function TaskType({ taskType, onChange }) {
  return (
    <div className="flex items-center my-2">
      <h4 className="text-l font-semibold pr-4">Task Type</h4>
      <div className="inline-flex items-center w-max h-10 gap-2.5">
        <Select options={taskOptions} value={taskType} onChange={onChange} />
      </div>
    </div>
  );
}
