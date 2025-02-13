import os
from typing import Any, List, Dict, Optional

import numpy as np
import pandas as pd
from generic_utils import format_sql, make_request, normalize_sql
from oracle.celery_app import LOGGER
from oracle.constants import TaskType
from db_oracle_utils import update_status
import asyncio

Z_THRESHOLD = 3  # z-score threshold for anomalies
NUMERIC_DTYPES = [np.float64, np.int64]
DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")

# explore module constants
FETCHED_TABLE_CSV = "fetched_table_csv"  # raw table fetched using sql
TABLE_CSV = "table_csv"  # table represented in the chart
ANOMALIES_CSV = "anomalies_csv"  # anomalies in the data
CORRELATION = "correlation"  # correlation between x and y columns


async def gen_sql(
    api_key: str,
    db_type: str,
    question: str,
    glossary: str,
    hard_filters: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Generate SQL for the given question and glossary, using the Defog API.
    """
    resp = await make_request(
        f"{DEFOG_BASE_URL}/generate_query_chat",
        data={
            "api_key": api_key,
            "dev": False,
            "db_type": db_type,
            "question": question,
            "glossary": glossary,
            "hard_filters": hard_filters,
        },
        log_time=True,
    )
    # anything that returns a status code other than 200 will return None
    if resp:
        gen_sql = resp["sql"]
        gen_sql = normalize_sql(gen_sql)
        LOGGER.debug(f"Generated SQL: {format_sql(gen_sql)}")
        return gen_sql
    else:
        raise Exception(f"Error in making request to /generate_query_chat")


async def retry_sql_gen(
    api_key: str, question: str, sql: str, error: str, db_type: str
) -> Optional[str]:
    """
    Fix the error that occurred while generating SQL / executing the query.
    Returns the fixed sql query if successful, else None.
    """
    json_data = {
        "api_key": api_key,
        "question": question,
        "previous_query": sql,
        "error": error,
        "db_type": db_type,
    }
    response = await make_request(
        f"{DEFOG_BASE_URL}/retry_query_after_error",
        data=json_data,
        log_time=True,
    )
    if response:
        new_query = response["new_query"]
        return new_query
    else:
        raise Exception(f"Error in making request to /retry_query_after_error")


# sub-routines for getting summaries / percentiles:
def get_mean(data: pd.Series) -> float:
    return data.mean()


def get_pct_05(data: pd.Series) -> float:
    return data.quantile(0.05)


def get_pct_25(data: pd.Series) -> float:
    return data.quantile(0.25)


def get_median(data: pd.Series) -> float:
    return data.median()


def get_pct_75(data: pd.Series) -> float:
    return data.quantile(0.75)


def get_pct_95(data: pd.Series) -> float:
    return data.quantile(0.95)


def histogram(data: pd.Series) -> pd.DataFrame:
    print(f"index: {data.index}, name: {data.name}")
    # drop na/infinite values
    vals = data.dropna(inplace=False).values
    vals = vals[vals != np.inf]
    # we use auto because seaborn defaults to auto bins
    counts, bin_edges = np.histogram(vals, bins="auto")
    # bin_edges has 1 more element than counts
    return pd.DataFrame(
        {"count": counts}, index=pd.Index(bin_edges[:-1], name=f"bin_{data.name}")
    )


def get_chart_df(data: pd.DataFrame, chart_fn_params: Dict[str, Any]) -> pd.DataFrame:
    """
    Performs any necessary data aggregations on data, and returns the dataframe
    representing the underlying data used to plot the chart.
    """
    chart_fn = chart_fn_params["name"]
    kwargs = chart_fn_params.get("parameters", {})
    kind = kwargs.get("kind", None)
    # 1-to-1 mapping of rows to chart elements
    if chart_fn == "relplot" and kind == "scatter":
        data_cols = []
        for col in ["x", "y", "hue", "col", "row"]:
            if col in kwargs and kwargs[col]:
                data_cols.append(kwargs[col])
        return data[data_cols]
    # many-to-1 mapping of rows to chart elements using an aggregate function
    elif (chart_fn == "relplot" and kind == "line") or (
        chart_fn == "catplot" and kind == "bar"
    ):
        agg_cols = []
        y_col = kwargs.get("y", None)
        if not y_col or y_col not in data.columns:
            LOGGER.error(f"y column not found in data: {y_col}")
            return data
        if data[y_col].dtype not in [np.float64, np.int64]:
            LOGGER.error(f"y column is not numeric: {y_col}")
            return data
        for col in ["x", "hue", "col", "row"]:
            if col in kwargs and kwargs[col]:
                agg_cols.append(kwargs[col])
        # get the default mean and 5th/95th percentiles
        data_agg = (
            data[agg_cols + [y_col]]
            .groupby(agg_cols)
            .agg(
                {
                    y_col: [
                        ("mean", get_mean),
                        ("pct_05", get_pct_05),
                        ("pct_95", get_pct_95),
                    ]
                }
            )
            .reset_index()
        )
        # flatten multi-index columns
        data_agg.columns = [
            f"{col[0]}_{col[1]}" if col[1] else col[0] for col in data_agg.columns
        ]
        return data_agg
    # many-to-1 mapping of rows to chart elements using distribution
    elif chart_fn == "catplot" and (kind == "box" or kind == "violin"):
        agg_cols = []
        y_col = kwargs.get("y", None)
        if not y_col or y_col not in data.columns:
            LOGGER.error(f"y column not found in data: {y_col}")
            return data
        if data[y_col].dtype not in [np.float64, np.int64]:
            LOGGER.error(f"y column is not numeric: {y_col}")
            return data
        for col in ["x", "hue", "col", "row"]:
            if col in kwargs and kwargs[col]:
                agg_cols.append(kwargs[col])
        dist_data = (
            data.groupby(agg_cols)
            .agg(
                {
                    y_col: [
                        ("pct_05", get_pct_05),
                        ("pct_25", get_pct_25),
                        ("pct_50", get_median),
                        ("pct_75", get_pct_75),
                        ("pct_95", get_pct_95),
                    ]
                }
            )
            .reset_index()
        )
        # flatten multi-index columns
        dist_data.columns = [
            f"{col[0]}_{col[1]}" if col[1] else col[0] for col in dist_data.columns
        ]
        return dist_data
    elif chart_fn == "displot" and kind == "hist":
        agg_cols = []
        x_col = kwargs.get("x", None)
        for col in ["hue", "col", "row"]:
            if col in kwargs and kwargs[col]:
                agg_cols.append(kwargs[col])
        # calculate histogram grouped by agg_cols
        if agg_cols:
            histogram_data = data.groupby(agg_cols).apply(
                lambda x: histogram(x[x_col]), include_groups=False
            )
        else:
            histogram_data = histogram(data[x_col])
        histogram_data = histogram_data.reset_index()
        return histogram_data
    else:
        LOGGER.error(
            f"Edge case not handled for chart_fn: {chart_fn}, chart params: {chart_fn_params}"
        )
        return data


def get_correlation(
    data: pd.DataFrame, chart_fn_params: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Get the correlation between the x and y columns.
    """
    kwargs = chart_fn_params.get("parameters", {})
    x_col = kwargs.get("x", None)
    y_col = kwargs.get("y", None)
    if not x_col or not y_col or x_col not in data.columns or y_col not in data.columns:
        LOGGER.debug(f"x or y column not found in data: {x_col}, {y_col}")
        return None
    if (
        pd.api.types.is_numeric_dtype(data[x_col]) is False
        or pd.api.types.is_numeric_dtype(data[y_col]) is False
    ):
        LOGGER.debug(
            f"x or y column is not numeric. dtypes: {data[x_col].dtype}, {data[y_col].dtype}"
        )
        return None
    return {
        "x_col": x_col,
        "y_col": y_col,
        "correlation": data[x_col].corr(data[y_col], method="spearman"),
    }


def get_anomalies(
    chart_df: pd.DataFrame,
    chart_fn_params: Dict[str, Any],
    z_threshold: int = Z_THRESHOLD,
) -> Optional[pd.DataFrame]:
    """
    Get anomalies in the data using a simple z-score method.
    The data supplied should ideally be the data represented in the chart.
    Returns a dataframe of anomalies and None if inputs are invalid or no
    anomalies are found.
    """
    chart_fn = chart_fn_params["name"]
    kwargs = chart_fn_params.get("parameters", {})
    kind = kwargs.get("kind", None)
    y_colname_original = kwargs.get("y", None)
    if y_colname_original:
        non_y_columns = [
            col for col in chart_df.columns if not col.startswith(y_colname_original)
        ]
    # hist charts have no y column, and only numeric columns can have z-scores
    if chart_fn == "displot":
        return None
    # box/violin plots have multiple y columns, and requires a different method
    elif chart_fn == "catplot" and (kind == "box" or kind == "violin"):
        # TODO use other distribution statistics to calculate z-scores
        return None
    # get list of y column names depending on the earlier processing (e.g. aggregation)
    if chart_fn == "relplot" and kind == "scatter":
        y_colname = y_colname_original
    elif (chart_fn == "relplot" and kind == "line") or (
        chart_fn == "catplot" and kind == "bar"
    ):
        y_colname = f"{y_colname_original}_mean"
    else:
        raise ValueError(
            f"Unsupported chart_fn x kind combination: {chart_fn} x {kind}"
        )
    if y_colname not in chart_df.columns:
        LOGGER.error(f"y column not found in data: {y_colname}")
        return None
    if chart_df[y_colname].dtype not in [np.float64, np.int64]:
        LOGGER.error(f"y column is not numeric: {y_colname}")
        return None

    # iterate through each record, and see if it is within the z-threshold calculated without it
    anomalies = []
    y_col = chart_df[y_colname]
    columns_to_keep = non_y_columns + [y_colname]
    for i, row in chart_df.iterrows():
        # get the mean and std of the data without the row
        y_no_row = y_col.drop(i, inplace=False)
        y_mean = y_no_row.mean()
        y_std = y_no_row.std()
        z_score = (row[y_colname] - y_mean) / y_std
        if abs(z_score) > z_threshold:
            row_to_keep = row[columns_to_keep]
            row_to_keep[f"{y_colname}_zscore"] = z_score
            anomalies.append(row_to_keep)
    if anomalies:
        anomalies_df = pd.DataFrame(anomalies)
        return anomalies_df
    else:
        return None


async def gen_data_analysis(
    task_type: TaskType,
    api_key: str,
    generated_qn: str,
    sql: str,
    analysis_data: pd.DataFrame = None,
    data_anomalies: pd.DataFrame = None,
    correlation_dict: Optional[Dict[str, Any]] = None,
    chart_fn_params: Dict[str, Any] = None,
) -> Dict[str, str]:
    """
    Given the user question, generated question and fetched data and chart,
    this will generate a title and summary of the key insights.
    Returns a dictionary with the title and summary.
    """
    if data_anomalies is None:
        data_anomalies_csv = ""
    else:
        data_anomalies_csv = data_anomalies.to_csv(
            float_format="%.3f", header=True, index=False
        )
    json_data = {
        "task_type": task_type.value,
        "api_key": api_key,
        "question": generated_qn,
        "sql": sql,
        "data_csv": analysis_data.to_csv(float_format="%.2f", header=True, index=False),
        "data_anomalies_csv": data_anomalies_csv,
        "correlation_dict": correlation_dict,
        "chart_fn": chart_fn_params.get("name") if chart_fn_params else None,
        "chart_params": (
            chart_fn_params.get("parameters", {}) if chart_fn_params else {}
        ),
    }
    resp = await make_request(
        f"{DEFOG_BASE_URL}/oracle/gen_explorer_data_analysis", data=json_data
    )
    if resp:
        return resp
    else:
        raise Exception(
            f"Error in making request to /oracle/gen_explorer_data_analysis"
        )


async def independent_status_updater(report_id: int, generated_qns_summaries: list):
    """
    Update the status of the report in the based on the summaries of the generated questions.
    """
    LOGGER.info(f"Updating status for {len(generated_qns_summaries)} questions")
    for summary in generated_qns_summaries:
        # Update the status in the database
        await update_status(report_id, summary)
        # Delay between updates (in seconds)
        await asyncio.sleep(2)
    LOGGER.info(f"All {len(generated_qns_summaries)} statuses updated successfully.")
