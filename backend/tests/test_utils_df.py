from decimal import Decimal
import unittest
import pandas as pd
from pandas.testing import assert_series_equal
from utils_df import determine_column_type, mk_df


class TestDetermineColumnType(unittest.TestCase):

    def test_string_column(self):
        data = pd.Series(["a", "b", "c"])
        self.assertEqual(determine_column_type(data), "string")

    def test_integer_column(self):
        data = pd.Series([1, 2, 3])
        self.assertEqual(determine_column_type(data), "int64")

    def test_float_column(self):
        data = pd.Series([1.1, 2.2, 3.3])
        self.assertEqual(determine_column_type(data), "float64")

    def test_date_column(self):
        data = pd.Series(["2021-01-01", "2021-01-02", "2021-01-03"])
        self.assertEqual(determine_column_type(data), "date")
        data = pd.Series(["2021-01", "2021-02", "2021-03"])
        self.assertEqual(determine_column_type(data), "string")

    def test_year_column(self):
        data = pd.Series(["2021", "2022", "2023"])
        self.assertEqual(determine_column_type(data), "int64")

    def test_time_column(self):
        data = pd.Series(["12:00:00", "13:00:00", "14:00:00"])
        self.assertEqual(determine_column_type(data), "time")

    def test_datetime_column(self):
        data = pd.Series(
            ["2021-01-01 12:00:00", "2021-01-02 13:00:00", "2021-01-03 14:00:00"]
        )
        self.assertEqual(determine_column_type(data), "datetime")

    def test_mixed_str_date_column(self):
        data = pd.Series(["2021-01-01", "apple", "2021-01-03"])
        self.assertEqual(determine_column_type(data), "string")

    def test_mixed_date_datetime_column(self):
        data = pd.Series(["2021-01-01", "2021-01-02 13:00:00", "2021-01-03 14:00:00"])
        self.assertEqual(determine_column_type(data), "string")


class TestMkDf(unittest.TestCase):

    def test_string_column(self):
        data = [["a", "b", "c"], ["d", "e", "f"]]
        columns = ["col1", "col2", "col3"]
        df = mk_df(data, columns)
        self.assertTrue((df.dtypes == "object").all())

    def test_integer_column(self):
        data = [["1", "2", "3"], ["4", "5", "6"]]
        columns = ["col1", "col2", "col3"]
        df = mk_df(data, columns)
        for col in df.columns:
            self.assertTrue((pd.api.types.is_integer_dtype(df[col])))

    def test_float_column(self):
        data = [["1.1", "2.2", "3.3"], ["4.4", "5.5", "6.6"]]
        columns = ["col1", "col2", "col3"]
        df = mk_df(data, columns)
        for col in df.columns:
            self.assertTrue((pd.api.types.is_float_dtype(df[col])))

    def test_date_column(self):
        data = [
            ["2021-01-01", "2021-01-02"],
            ["2021-01-04", "2021-01-05"],
        ]
        columns = ["col1", "col2"]
        df = mk_df(data, columns)
        assert_series_equal(
            df["col1"],
            pd.Series(["2021-01-01", "2021-01-04"], dtype="datetime64[ns]"),
            check_dtype=True,
            check_names=False,
        )
        assert_series_equal(
            df["col2"],
            pd.Series(["2021-01-02", "2021-01-05"], dtype="datetime64[ns]"),
            check_dtype=True,
            check_names=False,
        )

    def test_year_column(self):
        data = [
            (Decimal("2021"), "1990", "2001-01"),
            (Decimal("2022"), "2022-01", "2002-04"),
        ]
        columns = ["col1", "col2", "col3"]
        df = mk_df(data, columns)
        assert_series_equal(
            df["col1"], pd.Series([2021, 2022]), check_dtype=True, check_names=False
        )
        assert_series_equal(
            df["col2"],
            pd.Series(["1990", "2022-01"]),
            check_dtype=True,
            check_names=False,
        )
        assert_series_equal(
            df["col3"],
            pd.Series(["2001-01", "2002-04"]),
            check_dtype=True,
            check_names=False,
        )
        self.assertTrue(pd.api.types.is_integer_dtype(df["col1"]))
        self.assertTrue(pd.api.types.is_object_dtype(df["col2"]))
        self.assertTrue(pd.api.types.is_object_dtype(df["col3"]))

    def test_time_column(self):
        data = [
            ["12:00:00", "13:00:00", "14:00:00"],
            ["15:00:00", "16:00:00", "17:00:00"],
        ]
        columns = ["col1", "col2", "col3"]
        df = mk_df(data, columns)
        self.assertTrue((df.dtypes == "object").all())

    def test_datetime_column(self):
        data = [
            ["2021-01-01 12:00:00", "2021-01-02 13:00:00", "2021-01-03 14:00:00"],
            ["2021-01-04 15:00:00", "2021-01-05 16:00:00", "2021-01-06 17:00:00"],
        ]
        columns = ["col1", "col2", "col3"]
        df = mk_df(data, columns)
        self.assertTrue((df.dtypes == "datetime64[ns]").all())

    def test_mixed_types(self):
        data = [
            ["2021-01-01", "1", "banana"],
            ["2021-01-02", "2", "2.2"],
            ["apple", "3.3", "3.3"],
        ]
        columns = ["col1", "col2", "col3"]
        df = mk_df(data, columns)
        self.assertTrue(pd.api.types.is_object_dtype(df["col1"]))
        self.assertTrue(pd.api.types.is_float_dtype(df["col2"]))
        self.assertTrue(pd.api.types.is_object_dtype(df["col3"]))

    def test_mixed_types_2(self):
        data = [
            (Decimal("2023"), "Student Store", 11926004, None),
            (Decimal("2024"), "Student Store", 7813075, Decimal("-34.48")),
        ]
        columns = [
            "enrollment_year",
            "channel",
            "total_activations",
            "percentage_change",
        ]
        df = mk_df(data, columns)
        assert_series_equal(
            df["enrollment_year"],
            pd.Series([2023, 2024]),
            check_dtype=True,
            check_names=False,
        )
        assert_series_equal(
            df["channel"],
            pd.Series(["Student Store", "Student Store"]),
            check_dtype=True,
            check_names=False,
        )
        assert_series_equal(
            df["total_activations"],
            pd.Series([11926004, 7813075]),
            check_dtype=True,
            check_names=False,
        )
        assert_series_equal(
            df["percentage_change"],
            pd.Series([None, Decimal("-34.48")]),
            check_dtype=True,
            check_names=False,
        )
        self.assertTrue(pd.api.types.is_integer_dtype(df["enrollment_year"]))
        self.assertTrue(pd.api.types.is_object_dtype(df["channel"]))
        self.assertTrue(pd.api.types.is_integer_dtype(df["total_activations"]))
        self.assertTrue(pd.api.types.is_object_dtype(df["percentage_change"]))
