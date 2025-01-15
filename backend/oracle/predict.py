import os
import time
import traceback
from typing import Any, Dict, List

from celery.utils.log import get_task_logger
from prophet import Prophet
from prophet.serialize import model_to_json
import pandas as pd

from db_utils import get_db_type_creds
from generic_utils import make_request
from oracle.constants import TaskType
from oracle.utils_explore_data import FIGSIZE, gen_sql, retry_sql_gen
from utils_logging import LOG_LEVEL, save_and_log, save_timing, truncate_obj
from utils_sql import execute_sql

RETRY_DATA_FETCH = 1
DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
TIME_SERIES = "time-series"
CLASSIFICATION = "classification"
REGRESSION = "regression"
OBJECTIVE_TYPES = [TIME_SERIES, CLASSIFICATION, REGRESSION]

LOGGER = get_task_logger(__name__)
LOGGER.setLevel(LOG_LEVEL)


async def predict(
    api_key: str,
    report_id: str,
    task_type: TaskType,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will make the necessary predictions, by training a machine learning
    model on the data provided, and generating predictions needed for the analysis.
    Here are the key steps:

    We will first start by getting the target variable and the features from the
    data, focusing on getting the following correct:
    - target variable and features to use and any transformations needed (e.g. log
        transformation, scaling, etc.) based on earlier explorations.
    - unit of prediction (individual, aggregate, time-period to aggregate / predict over etc.)
    - additional modeling constraints:
      - time-series:
        - saturating forecasts (cap and floor)
        - holidays / special days / events (e.g. black friday, a production outage)
    At the end of this stage, we should have
    - a dataframe with the target variable and features
    - list of column names
    - any additional keyword arguments needed for the model training.

    Next, we train the model on the data.

    Finally, we generate the predictions needed for the analysis, and save the
    intermediate model and predictions generated in the report_id's directory.

    Outputs:
    - objective_type: one of time-series, classification, regression
    - model_path: path where we save the exported model
    - working:
        - target: name of target variable used
        - features: name of features used
        - unit: unit of prediction used

    Side Effects:
    Intermediate model and predictions generated will be saved in the report_id's
    directory.
    """
    LOGGER.info(f"Predicting for report {report_id}")
    ts, timings = time.time(), []
    LOGGER.debug(f"inputs: {inputs}")
    LOGGER.debug(f"outputs:\n{truncate_obj(outputs)}")

    gather_context = outputs["gather_context"]
    problem_statement = gather_context["problem_statement"]
    context = gather_context["context"]
    explore = outputs["explore"]
    analyses = explore["analyses"]
    independent_variables = []
    for analysis in analyses:
        aiv = analysis.get("independent_variable")
        if not aiv:
            continue
        working = analysis.get("working")
        independent_variable = {
            "variable_name": aiv["name"],
            "variable_description": aiv["description"],
            "variable_generated_question": analysis["generated_qn"],
            "variable_data_summary": analysis.get("summary", "No summary available"),
            "variable_data_sql": working["generated_sql"],
        }
        independent_variables.append(independent_variable)
    dependent_variable = explore["dependent_variable"]
    dependent_variable_description = dependent_variable["description"]
    formulate_request = {
        "api_key": api_key,
        "problem_statement": problem_statement,
        "context": context,
        "dependent_variable_description": dependent_variable_description,
        "independent_variables": independent_variables,
    }
    formulate_response = await make_request(
        f"{DEFOG_BASE_URL}/oracle/predict/formulate",
        data=formulate_request,
    )
    prediction_sql_question = formulate_response.get("question")
    if not prediction_sql_question:
        raise Exception(
            "Could not get prediction question from /oracle/predict/formulate"
        )
    suggested_sql = formulate_response.get("suggested_sql")
    unit_of_analysis = formulate_response.get("unit_of_analysis")
    fit_kwargs = formulate_response.get("fit_kwargs", {})
    predict_kwargs = formulate_response.get("predict_kwargs", {})
    ts = save_timing(ts, "formulate prediction request", timings)

    db_type, db_creds = await get_db_type_creds(api_key)
    retry_data_fetch = inputs.get("retry_data_fetch", RETRY_DATA_FETCH)
    err_msg, sql, data = None, None, None
    retry_count = 0
    while retry_count <= retry_data_fetch:
        # TODO: DEF-540 generate SQL across multiple DB's and stitch them together with pandas
        # generate SQL
        try:
            if retry_count == 0:
                if not suggested_sql:
                    sql = await gen_sql(
                        api_key=api_key,
                        db_type=db_type,
                        question=prediction_sql_question,
                        glossary="",
                        hard_filters=[],
                    )
                else:
                    sql = suggested_sql
            else:
                LOGGER.debug(
                    f"Retrying SQL generation for prediction dataframe: {prediction_sql_question}"
                )
                sql = await retry_sql_gen(
                    api_key, prediction_sql_question, sql, err_msg, db_type
                )
            err_msg = None
        except Exception as e:
            LOGGER.error(f"Error occurred in generating SQL: {str(e)}")
            LOGGER.error(traceback.format_exc())
            err_msg = str(e)
            sql = None
        if sql:
            # fetch data
            ts = save_timing(
                ts, f"Prediction SQL generation (try {retry_count})", timings
            )
            data, err_msg = await execute_sql(db_type, db_creds, sql)
            if err_msg is not None:
                LOGGER.error(f"Error occurred in executing SQL: {err_msg}")
            else:
                break
        retry_count += 1
    if data is None:
        LOGGER.error(
            f"Data fetching failed for prediction dataframe: {prediction_sql_question}"
        )
        return None
    ts = save_timing(ts, f"fetch data", timings)

    # verify that we have ds and y columns
    if "ds" not in data.columns:
        raise ValueError("Missing 'ds' column in data")
    if "y" not in data.columns:
        raise ValueError("Missing 'y' column in data")
    # remove timezone info from ds column
    data["ds"] = pd.to_datetime(data["ds"]).dt.tz_localize(None)
    LOGGER.debug(f"Data shape: {data.shape}")
    LOGGER.debug(f"Data columns: {data.columns}")
    LOGGER.debug(f"Data head: {data.head()}")

    # create the directory to save the model
    current_dir = os.getcwd()
    report_model_dir = os.path.join(
        current_dir, f"oracle/reports/{api_key}/report_{report_id}"
    )
    os.makedirs(report_model_dir, exist_ok=True)
    model_path = os.path.join(report_model_dir, "model.json")

    # train model
    train_data_csv = data.to_csv(index=False, header=True, float_format="%.3f")
    LOGGER.debug(f"Using data to train: {train_data_csv}")
    model = fit_model(
        data, model_path, fit_kwargs
    )
    ts = save_timing(ts, "fit model", timings)

    # make predictions
    predictions = predict_data(model, predict_kwargs)
    LOGGER.debug(f"Predictions type: {type(predictions)}")
    predictions_csv = predictions[["ds", "yhat", "yhat_lower", "yhat_upper"]].to_csv(
        index=False, header=True, float_format="%.3f"
    )
    LOGGER.debug(f"Predictions: {predictions_csv}")
    ts = save_timing(ts, "predict data", timings)

    # chart predictions
    chart_kwargs = {
        "ylabel": dependent_variable_description,
    }
    chart_paths = chart_predictions(
        model, predictions, report_model_dir, chart_kwargs
    )
    LOGGER.debug(f"Chart paths: {chart_paths}")
    ts = save_timing(ts, "chart predictions", timings)

    # summarize predictions
    summarize_request = {
        "api_key": api_key,
        "problem_statement": problem_statement,
        "dependent_variable_description": dependent_variable_description,
        "unit_of_analysis": unit_of_analysis,
        "input_data_csv": train_data_csv,
        "predicted_data_csv": predictions_csv,
    }
    response = await make_request(
        f"{DEFOG_BASE_URL}/oracle/predict/summarize",
        data=summarize_request,
    )
    prediction_summary = response.get("summary")
    LOGGER.debug(f"Summarize response: {response}")
    save_and_log(ts, "summarize predictions", timings)

    outputs = {
        "model_path": model_path,
        "chart_paths": chart_paths,
        "working": {
            "target": dependent_variable_description,
            "features": "ds",
            "unit_of_analysis": unit_of_analysis,
            "prediction_sql": sql,
            "fit_kwargs": fit_kwargs,
            "predict_kwargs": predict_kwargs,
        },
        "predictions": predictions_csv,
        "prediction_summary": prediction_summary,
    }
    return outputs


def fit_model(
    data: pd.DataFrame,
    model_path: str,
    fit_kwargs: Dict[str, Any],
):
    """
    This function will train a machine learning model on the data provided.
    """
    model = Prophet()
    model.fit(data)
    model_json = model_to_json(model)
    with open(model_path, "w") as f:
        f.write(model_json)
    return model


def predict_data(
    model: Prophet,
    predict_kwargs: Dict[str, Any],
) -> pd.DataFrame:
    """
    This function will generate predictions based on the model trained.
    """
    future = model.make_future_dataframe(
        periods=predict_kwargs.get("periods", 1),
        freq=predict_kwargs.get("freq", "D"),
    )
    forecast = model.predict(future)
    return forecast


def chart_predictions(
    model: Prophet,
    forecast: pd.DataFrame,
    chart_dir: str,
    chart_kwargs: Dict[str, Any] = {},
) -> List[str]:
    """
    This function will generate a chart based on the predictions generated.
    """
    xlabel = chart_kwargs.get("xlabel", "Date")
    ylabel = chart_kwargs.get("ylabel")
    fig = model.plot(forecast, xlabel=xlabel, ylabel=ylabel, figsize=FIGSIZE)
    path_forecast = os.path.join(chart_dir, "forecast.png")
    fig.savefig(path_forecast)
    # plot components and save
    fig = model.plot_components(forecast, figsize=FIGSIZE)
    path_components = os.path.join(chart_dir, "components.png")
    fig.savefig(path_components)
    return [path_forecast, path_components]
