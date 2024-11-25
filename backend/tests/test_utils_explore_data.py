import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from oracle.utils_explore_data import (
    get_chart_df,
    histogram,
)


class TestGetHistogram(unittest.TestCase):

    def test_histogram_small(self):
        data = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
        result = histogram(data["x"])
        print(result)
        expected_df = pd.DataFrame(
            data={"count": [1, 1, 1, 2]},
            index=pd.Index([1.0, 2.0, 3.0, 4.0], name="bin_x"),
        )
        assert_frame_equal(result, expected_df)

    def test_histogram_large_shuffled(self):
        # 1 to 10 repeated 10 times each
        data = np.repeat(np.arange(1, 11), 10)
        data_shuffled = np.random.permutation(data)
        data = pd.DataFrame({"x": data_shuffled})
        result = histogram(data["x"])
        print(result)
        expected_df = pd.DataFrame(
            {"count": [20, 10, 10, 10, 10, 10, 10, 20]},
            index=pd.Index(
                [1.0, 2.125, 3.25, 4.375, 5.5, 6.625, 7.75, 8.875], name="bin_x"
            ),
        )
        assert_frame_equal(result, expected_df)

    def test_histogram_grouped(self):
        data = pd.DataFrame(
            {
                "x": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                "hue": ["A", "A", "B", "B", "A", "A", "B", "B", "A"],
            }
        )
        result = (
            data.groupby("hue")
            .apply(lambda x: histogram(x["x"]), include_groups=False)
            .reset_index(names=["hue", "bin", "count"])
        )
        print(result)
        expected_df = pd.DataFrame(
            {
                "hue": ["A", "A", "A", "A", "B", "B", "B"],
                "bin": [1.0, 3.0, 5.0, 7.0, 3.0, 4.0 + 2 / 3, 6.0 + 1 / 3],
                "count": [2, 0, 2, 1, 2, 0, 2],
            }
        )
        assert_frame_equal(result, expected_df, check_exact=False)


class TestGetChartDf(unittest.TestCase):

    def setUp(self):
        self.data_xy = pd.DataFrame(
            {
                "version": [1, 2, 3, 4, 5, 6],
                "sales": [10, 20, 30, 40, 50, 60],
            }
        )
        self.data_xy_hue = pd.DataFrame(
            {
                "version": [1, 2, 3, 1, 2, 3],
                "sales": [10, 20, 30, 40, 50, 60],
                "category": ["A", "A", "A", "B", "B", "B"],
            }
        )

    def test_relplot_scatter_xy(self):
        chart_fn_params = {
            "name": "relplot",
            "parameters": {
                "kind": "scatter",
                "x": "version",
                "y": "sales",
            },
        }
        result = get_chart_df(self.data_xy_hue, chart_fn_params)
        expected_df = self.data_xy_hue[["version", "sales"]]
        assert_frame_equal(result, expected_df)
        result = get_chart_df(self.data_xy, chart_fn_params)
        assert_frame_equal(result, self.data_xy)

    def test_relplot_scatter_xy_hue(self):
        chart_fn_params = {
            "name": "relplot",
            "parameters": {
                "kind": "scatter",
                "x": "version",
                "y": "sales",
                "hue": "category",
            },
        }
        result = get_chart_df(self.data_xy_hue, chart_fn_params)
        assert_frame_equal(result, self.data_xy_hue)

    def test_relplot_line_xy(self):
        chart_fn_params = {
            "name": "relplot",
            "parameters": {
                "kind": "line",
                "x": "version",
                "y": "sales",
            },
        }
        result = get_chart_df(self.data_xy_hue, chart_fn_params)
        expected_df = pd.DataFrame(
            {
                "version": [1, 2, 3],
                "sales_mean": [25.0, 35.0, 45.0],
                "sales_pct_05": [11.5, 21.5, 31.5],
                "sales_pct_95": [38.5, 48.5, 58.5],
            }
        )
        assert_frame_equal(result, expected_df)
        result = get_chart_df(self.data_xy, chart_fn_params)
        expected_df = pd.DataFrame(
            {
                "version": [1, 2, 3, 4, 5, 6],
                "sales_mean": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "sales_pct_05": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "sales_pct_95": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            }
        )
        assert_frame_equal(result, expected_df)

    def test_relplot_line_xy_hue(self):
        chart_fn_params = {
            "name": "relplot",
            "parameters": {
                "kind": "line",
                "x": "version",
                "y": "sales",
                "hue": "category",
            },
        }
        result = get_chart_df(self.data_xy_hue, chart_fn_params)
        expected_df = pd.DataFrame(
            {
                "version": [1, 1, 2, 2, 3, 3],
                "category": ["A", "B", "A", "B", "A", "B"],
                "sales_mean": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
                "sales_pct_05": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
                "sales_pct_95": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
            }
        )
        assert_frame_equal(result, expected_df)

    def test_catplot_bar_xy(self):
        chart_fn_params = {
            "name": "catplot",
            "parameters": {
                "kind": "bar",
                "x": "version",
                "y": "sales",
            },
        }
        result = get_chart_df(self.data_xy_hue, chart_fn_params)
        expected_df = pd.DataFrame(
            {
                "version": [1, 2, 3],
                "sales_mean": [25.0, 35.0, 45.0],
                "sales_pct_05": [11.5, 21.5, 31.5],
                "sales_pct_95": [38.5, 48.5, 58.5],
            }
        )
        assert_frame_equal(result, expected_df)
        result = get_chart_df(self.data_xy, chart_fn_params)
        expected_df = pd.DataFrame(
            {
                "version": [1, 2, 3, 4, 5, 6],
                "sales_mean": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "sales_pct_05": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "sales_pct_95": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            }
        )
        assert_frame_equal(result, expected_df)

    def test_catplot_bar_xy_hue(self):
        chart_fn_params = {
            "name": "catplot",
            "parameters": {
                "kind": "bar",
                "x": "version",
                "y": "sales",
                "hue": "category",
            },
        }
        result = get_chart_df(self.data_xy_hue, chart_fn_params)
        expected_df = pd.DataFrame(
            {
                "version": [1, 1, 2, 2, 3, 3],
                "category": ["A", "B", "A", "B", "A", "B"],
                "sales_mean": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
                "sales_pct_05": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
                "sales_pct_95": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
            }
        )
        assert_frame_equal(result, expected_df)

    def test_catplot_box_xy(self):
        chart_fn_params = {
            "name": "catplot",
            "parameters": {
                "kind": "box",
                "x": "version",
                "y": "sales",
            },
        }
        result = get_chart_df(self.data_xy_hue, chart_fn_params)
        expected_df = pd.DataFrame(
            {
                "version": [1, 2, 3],
                "sales_pct_05": [11.5, 21.5, 31.5],
                "sales_pct_25": [17.5, 27.5, 37.5],
                "sales_pct_50": [25.0, 35.0, 45.0],
                "sales_pct_75": [32.5, 42.5, 52.5],
                "sales_pct_95": [38.5, 48.5, 58.5],
            }
        )
        assert_frame_equal(result, expected_df)
        result = get_chart_df(self.data_xy, chart_fn_params)
        expected_df = pd.DataFrame(
            {
                "version": [1, 2, 3, 4, 5, 6],
                "sales_pct_05": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "sales_pct_25": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "sales_pct_50": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "sales_pct_75": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "sales_pct_95": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            }
        )
        assert_frame_equal(result, expected_df)

    def test_catplot_box_xy_hue(self):
        chart_fn_params = {
            "name": "catplot",
            "parameters": {
                "kind": "box",
                "x": "version",
                "y": "sales",
                "hue": "category",
            },
        }
        result = get_chart_df(self.data_xy_hue, chart_fn_params)
        expected_df = pd.DataFrame(
            {
                "version": [1, 1, 2, 2, 3, 3],
                "category": ["A", "B", "A", "B", "A", "B"],
                "sales_pct_05": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
                "sales_pct_25": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
                "sales_pct_50": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
                "sales_pct_75": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
                "sales_pct_95": [10.0, 40.0, 20.0, 50.0, 30.0, 60.0],
            }
        )
        assert_frame_equal(result, expected_df)

    def test_displot_hist_x(self):
        chart_fn_params = {
            "name": "displot",
            "parameters": {
                "kind": "hist",
                "x": "sales",
            },
        }
        result = get_chart_df(self.data_xy_hue, chart_fn_params)
        print(result)
        expected_df = pd.DataFrame(
            {
                "bin_sales": [10.0, 22.5, 35.0, 47.5],
                "count": [2, 1, 1, 2],
            }
        )
        assert_frame_equal(result, expected_df)

    def test_displot_hist_x_hue(self):
        chart_fn_params = {
            "name": "displot",
            "parameters": {
                "kind": "hist",
                "x": "sales",
                "hue": "category",
            },
        }
        result = get_chart_df(self.data_xy_hue, chart_fn_params)
        print(result)
        expected_df = pd.DataFrame(
            {
                "category": ["A", "A", "A", "B", "B", "B"],
                "bin_sales": [
                    10.0,
                    16.0 + 2 / 3,
                    23.0 + 1 / 3,
                    40.0,
                    46.0 + 2 / 3,
                    53.0 + 1 / 3,
                ],
                "count": [1, 1, 1, 1, 1, 1],
            }
        )
        assert_frame_equal(result, expected_df)

    # def test_edge_case(self):
    #     chart_fn_params = {"name": "unknown", "parameters": {}}
    #     result = get_chart_df(self.data, chart_fn_params)
    #     self.assertTrue(result.equals(self.data))
