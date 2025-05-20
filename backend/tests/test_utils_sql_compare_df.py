import pandas as pd
from utils_sql import compare_df, subset_df


def test_compare_df_equal():
    df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    df2 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    assert compare_df(df1, df2, question="test") is True


def test_compare_df_shape_mismatch():
    df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    df2 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    assert not compare_df(df1, df2, question="test")


def test_compare_df_value_mismatch():
    df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    df2 = pd.DataFrame({'a': [1, 99], 'b': [3, 4]})
    assert not compare_df(df1, df2, question="test")

def test_compare_df_mixed_types_equal():
    df1 = pd.DataFrame({
        'int_col': [1, 2],
        'float_col': [1.5, 2.5],
        'date_col': pd.to_datetime(['2023-01-01', '2023-01-02']),
        'str_col': ['x', 'y'],
    })
    df2 = df1.copy()
    assert compare_df(df1, df2, question="mixed") is True


def test_compare_df_mixed_types_value_mismatch():
    df1 = pd.DataFrame({
        'int_col': [1, 2],
        'float_col': [1.5, 2.5],
        'date_col': pd.to_datetime(['2023-01-01', '2023-01-02']),
        'str_col': ['x', 'y'],
    })
    df2 = df1.copy()
    df2.loc[1, 'float_col'] = 9.9
    assert not compare_df(df1, df2, question="mixed")


def test_subset_df_columns_subset_true():
    df_gold = pd.DataFrame({
        'int_col': [1, 2],
        'str_col': ['x', 'y'],
    })
    df_gen = pd.DataFrame({
        'int_col': [1, 2],
        'str_col': ['x', 'y'],
        'float_col': [0.1, 0.2],
        'date_col': pd.to_datetime(['2023-01-01', '2023-01-02']),
    })
    assert subset_df(df_gold, df_gen, question="subset") is True


def test_subset_df_extra_rows_false():
    df_gold = pd.DataFrame({
        'int_col': [1, 2],
        'str_col': ['x', 'y'],
    })
    df_gen = pd.DataFrame({
        'int_col': [1, 2, 3],
        'str_col': ['x', 'y', 'z'],
        'float_col': [0.1, 0.2, 0.3],
        'date_col': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
    })
    assert not subset_df(df_gold, df_gen, question="subset")

