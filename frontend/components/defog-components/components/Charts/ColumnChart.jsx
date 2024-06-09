import React from "react";
import ErrorBoundary from "../common/ErrorBoundary";
import { Row, Col } from "antd";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

import { setChartJSDefaults } from "../common/utils";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const ColumnChart = React.memo(
  ({ chartConfig, title, height, xAxisIsDate, theme }) => {
    const { chartLabels, chartData } = chartConfig;
    setChartJSDefaults(ChartJS, title, xAxisIsDate, theme);

    return (
      <ErrorBoundary>
        <Row justify={"center"}>
          <Col md={{ span: 24 }} lg={12}>
            <div className="column-chart-ctr" style={{ height: height }}>
              <Bar
                data={{
                  labels: chartLabels,
                  datasets: chartData.map((d) => ({
                    ...d,
                  })),
                }}
              ></Bar>
            </div>
          </Col>
        </Row>
      </ErrorBoundary>
    );
  },
  () => false
);

ColumnChart.displayName = "ColumnChart";

export default ColumnChart;
