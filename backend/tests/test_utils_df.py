import datetime
from decimal import Decimal
import unittest
import pandas as pd
from pandas.testing import assert_series_equal
from utils_df import determine_column_type, mk_df, get_columns_summary


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

    def test_determine_column_type_money(self):
        test_cases = [
            ["$1,234.56", "$2,345.67"],
            ["$1.23", "$4.56"],
            ["1,234.56", "2,345.67"],
            ["$1,234", "$2,345"],
            ["1,234", "2,345.00"],
            ["$123456.78", "$78910.11"],
        ]
        
        for case in test_cases:
            series = pd.Series(case)

            assert determine_column_type(series) == "money"


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

    def test_mk_df_money_conversion(self):
        data = [
            ["$1,234.56", "A", "1"],
            ["$12,345.67", "B", "2"],
            ["$123,456.78", "C", "3"]
        ]
        columns = ["amount", "label", "id"]
        
        df = mk_df(data, columns)
        
        # Check if conversion to float was successful
        assert df.dtypes["amount"] == "float64"
        assert df["amount"].tolist() == [1234.56, 12345.67, 123456.78]
        
        # Test with different money formats
        data_varied = [
            ["$1,234.56", "A", "1"],
            ["1,234.56", "B", "2"],    # No dollar sign
            ["$1234.56", "C", "3"],    # No comma
            ["$1,234", "D", "4"]       # No cents
        ]
        
        df_varied = mk_df(data_varied, columns)
        assert df_varied.dtypes["amount"] == "float64"
        assert df_varied["amount"].tolist() == [1234.56, 1234.56, 1234.56, 1234.0]

    def test_get_columns_summary(self):
        # Create test data with mixed types
        data = [
            [datetime.date(2023, 1, 1), 'A', 10, 1.5, datetime.datetime(2023, 1, 1, 10, 0)],
            [datetime.date(2023, 1, 2), 'B', 20, 2.5, datetime.datetime(2023, 1, 2, 11, 0)],
            [datetime.date(2023, 1, 3), 'A', 30, 3.5, datetime.datetime(2023, 1, 3, 12, 0)],
            [datetime.date(2023, 1, 4), 'C', 40, 4.5, datetime.datetime(2023, 1, 4, 13, 0)]
        ]
        columns = ['dt_col', 'category', 'int_col', 'float_col', 'datetime_col']
        df = mk_df(data, columns)
        
        numeric_summary, non_numeric_summary, date_summary = get_columns_summary(df)
        
        # Check numeric summary format and content
        expected_numeric_summary = """,int_col,float_col
count,4.00,4.00
mean,25.00,3.00
std,12.91,1.29
min,10.00,1.50
25%,17.50,2.25
50%,25.00,3.00
75%,32.50,3.75
max,40.00,4.50
"""
        self.assertEqual(numeric_summary, expected_numeric_summary)
        
        # Check non-numeric summary format and content
        expected_non_numeric_summary = """,category
count,4
unique,3
top,A
freq,2
"""
        self.assertEqual(non_numeric_summary, expected_non_numeric_summary)
        
        # Check date summary format and content
        expected_date_summary = """Column name: dt_col
Value counts:
dt_col,count
2023-01-01,1
2023-01-02,1
2023-01-03,1
2023-01-04,1

Column name: datetime_col
Value counts:
datetime_col,count
2023-01-01 10:00:00,1
2023-01-02 11:00:00,1
2023-01-03 12:00:00,1
2023-01-04 13:00:00,1

"""
        self.assertEqual(date_summary, expected_date_summary)

    def test_get_columns_summary_empty_categories(self):
        # Test with missing category types
        data = [
            ['A', 10],
            ['B', 20],
            ['C', 30]
        ]
        columns = ['category', 'value']
        df = mk_df(data, columns)
        
        numeric_summary, non_numeric_summary, date_summary = get_columns_summary(df)
        
        # Should have numeric and non-numeric summaries but empty date summary
        self.assertNotEqual(numeric_summary, '')
        self.assertNotEqual(non_numeric_summary, '')
        self.assertEqual(date_summary, '')

    def test_get_columns_summary_all_numeric(self):
        # Test with only numeric data
        data = [
            [1, 1.5],
            [2, 2.5],
            [3, 3.5]
        ]
        columns = ['int_col', 'float_col']
        df = mk_df(data, columns)
        
        numeric_summary, non_numeric_summary, date_summary = get_columns_summary(df)
        
        # Should only have numeric summary
        self.assertNotEqual(numeric_summary, '')
        self.assertEqual(non_numeric_summary, '')
        self.assertEqual(date_summary, '')
