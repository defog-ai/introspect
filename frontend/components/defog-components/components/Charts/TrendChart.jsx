import React from "react";
import { Row, Col } from "antd";
import ErrorBoundary from "../common/ErrorBoundary";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { setChartJSDefaults } from "../common/utils";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const TrendChart = React.memo(
  ({ chartConfig, title, height, xAxisIsDate, theme }) => {
    const { chartLabels, chartData } = chartConfig;
    setChartJSDefaults(ChartJS, title, xAxisIsDate, theme);

    Object.assign(ChartJS.defaults.elements.point, {
      borderWidth: 0,
      radius: 5,
      hitRadius: 10,
      hoverRadius: 5,
    });

    if (chartData instanceof Array) {
      return (
        <ErrorBoundary>
          <Row justify={"center"}>
            <Col md={{ span: 24 }} lg={12}>
              <div className="pie-chart-ctr" style={{ height: height + "px" }}>
                <Line
                  data={{
                    labels: chartLabels,
                    datasets: chartData.map((d) => ({
                      ...d,
                      tension: 0.2,
                    })),
                  }}
                ></Line>
              </div>
            </Col>
          </Row>
        </ErrorBoundary>
      );
    } else {
      return <div></div>;
    }
  },
  () => false
);

TrendChart.displayName = "TrendChart";

export default TrendChart;
