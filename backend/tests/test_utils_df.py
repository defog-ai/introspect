import unittest
import pandas as pd
from utils_df import determine_column_type, mk_df

class TestDetermineColumnType(unittest.TestCase):

    def test_string_column(self):
        data = pd.Series(['a', 'b', 'c'])
        self.assertEqual(determine_column_type(data), 'string')

    def test_integer_column(self):
        data = pd.Series([1, 2, 3])
        self.assertEqual(determine_column_type(data), 'int64')

    def test_float_column(self):
        data = pd.Series([1.1, 2.2, 3.3])
        self.assertEqual(determine_column_type(data), 'float64')

    def test_date_column(self):
        data = pd.Series(['2021-01-01', '2021-01-02', '2021-01-03'])
        self.assertEqual(determine_column_type(data), 'date')
        data = pd.Series(['2021-01', '2021-02', '2021-03'])
        self.assertEqual(determine_column_type(data), 'date')
        data = pd.Series(['2021', '2022', '2023'])
        self.assertEqual(determine_column_type(data), 'date')

    def test_time_column(self):
        data = pd.Series(['12:00:00', '13:00:00', '14:00:00'])
        self.assertEqual(determine_column_type(data), 'time')

    def test_datetime_column(self):
        data = pd.Series(['2021-01-01 12:00:00', '2021-01-02 13:00:00', '2021-01-03 14:00:00'])
        self.assertEqual(determine_column_type(data), 'datetime')

    def test_mixed_str_date_column(self):
        data = pd.Series(['2021-01-01', 'apple', '2021-01-03'])
        self.assertEqual(determine_column_type(data), 'string')

    def test_mixed_date_datetime_column(self):
        data = pd.Series(['2021-01-01', '2021-01-02 13:00:00', '2021-01-03 14:00:00'])
        self.assertEqual(determine_column_type(data), 'string')


class TestMkDf(unittest.TestCase):

    def test_string_column(self):
        data = [['a', 'b', 'c'], ['d', 'e', 'f']]
        columns = ['col1', 'col2', 'col3']
        df = mk_df(data, columns)
        self.assertTrue((df.dtypes == 'object').all())

    def test_integer_column(self):
        data = [['1', '2', '3'], ['4', '5', '6']]
        columns = ['col1', 'col2', 'col3']
        df = mk_df(data, columns)
        for col in df.columns:
            self.assertTrue((pd.api.types.is_integer_dtype(df[col])))

    def test_float_column(self):
        data = [['1.1', '2.2', '3.3'], ['4.4', '5.5', '6.6']]
        columns = ['col1', 'col2', 'col3']
        df = mk_df(data, columns)
        for col in df.columns:
            self.assertTrue((pd.api.types.is_float_dtype(df[col])))

    def test_date_column(self):
        data = [['2021-01-01', '2021-01-02', '2021-01-03'], ['2021-01-04', '2021-01-05', '2021-01-06']]
        columns = ['col1', 'col2', 'col3']
        df = mk_df(data, columns)
        self.assertTrue((df.dtypes == 'datetime64[ns]').all())

    def test_time_column(self):
        data = [['12:00:00', '13:00:00', '14:00:00'], ['15:00:00', '16:00:00', '17:00:00']]
        columns = ['col1', 'col2', 'col3']
        df = mk_df(data, columns)
        self.assertTrue((df.dtypes == 'object').all())

    def test_datetime_column(self):
        data = [['2021-01-01 12:00:00', '2021-01-02 13:00:00', '2021-01-03 14:00:00'], ['2021-01-04 15:00:00', '2021-01-05 16:00:00', '2021-01-06 17:00:00']]
        columns = ['col1', 'col2', 'col3']
        df = mk_df(data, columns)
        self.assertTrue((df.dtypes == 'datetime64[ns]').all())

    def test_mixed_types(self):
        data = [['2021-01-01', '1', 'banana'], ['2021-01-02', '2', '2.2'], ['apple', '3.3', '3.3']]
        columns = ['col1', 'col2', 'col3']
        df = mk_df(data, columns)
        print(df.dtypes)
        self.assertTrue(pd.api.types.is_object_dtype(df['col1']))
        self.assertTrue(pd.api.types.is_float_dtype(df['col2']))
        self.assertTrue(pd.api.types.is_object_dtype(df['col3']))
