import re
import pandas as pd


def natural_sort_function(l, ascending=True):
    """
    Sorts a list or a pandas series in a natural way.
    If it's a list of numbers or datetimes, just sort them normally.
    If it's a string, check if there are numbers in the string, and sort them as a heirarchy of numbers.
    Example 1: ['a', 'b', 'c'] would be sorted as ['a', 'b', 'c']
    Example 2: ['1', '10', '2'] would be sorted as ['1', '2', '10']
    Example 3: ['a1', 'a10', 'a2'] would be sorted as ['a1', 'a2', 'a10']
    Example 4: ['C1D1', 'C10D10', 'C2D2', 'C1D11'] would be sorted as ['C1D1', 'C1D11', 'C2D2', 'C10D10']
    """

    def convert(text):
        return int(text) if text.isdigit() else text

    def alphanum_key(key):
        return [convert(c) for c in re.split("([0-9]+)", key)]

    if type(l) == pd.Series:
        # TODO do this in a more efficient way
        l = l.tolist()

    l.sort(key=alphanum_key, reverse=not ascending)
    return l


def natural_sort(df, time_column, units=None, ascending=True):
    """
    Sorts a dataframe in a natural way, using the natural_sort_function.
    """
    if df[time_column].dtype == "object":
        order = natural_sort_function(df[time_column].unique().tolist())
        df[time_column] = pd.Categorical(
            df[time_column], categories=order, ordered=True
        )
        if units:
            df = df.sort_values(by=[units, time_column], ascending=ascending)
        else:
            df = df.sort_values(by=time_column, ascending=ascending)
    else:
        df = df.sort_values(by=time_column, ascending=ascending)
    return df
