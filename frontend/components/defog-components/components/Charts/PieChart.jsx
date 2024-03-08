import React from "react";
import { Row, Col } from "antd";
import ErrorBoundary from "../common/ErrorBoundary";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { Pie } from "react-chartjs-2";
import { setChartJSDefaults } from "../common/utils";
import { chartColors } from "../../context/ThemeContext";

ChartJS.register(ArcElement, Tooltip, Legend);

const PieChart = React.memo(
  ({ chartConfig, title, height, xAxisIsDate, theme }) => {
    const { chartLabels, chartData } = chartConfig;
    setChartJSDefaults(ChartJS, title, xAxisIsDate, theme, true);

    return (
      <ErrorBoundary>
        <Row justify={"center"}>
          {/* don't nest pie charts */}
          {chartData.map((d) => {
            return (
              <Col
                md={{ span: 24 }}
                lg={12}
                key={d.label + d.data.map((_) => _[d.parsing.key]).join("__")}
              >
                <div
                  className="pie-chart-ctr"
                  style={{ height: height + "px" }}
                >
                  <Pie
                    data={{
                      labels: chartLabels,
                      datasets: [
                        {
                          ...d,
                          // pie chart specific.
                          backgroundColor: chartColors,
                        },
                      ],
                    }}
                    // pie chart specific.
                    options={{
                      plugins: {
                        title: {
                          display: true,
                          text: d.label,
                        },
                      },
                    }}
                  ></Pie>
                </div>
              </Col>
            );
          })}
        </Row>
      </ErrorBoundary>
    );
  },
  () => false
);

PieChart.displayName = "PieChart";

export default PieChart;
