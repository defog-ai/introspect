import time
from typing import Any, Dict

from celery.utils.log import get_task_logger

from utils_logging import LOG_LEVEL, save_and_log, save_timing, truncate_obj

LOGGER = get_task_logger(__name__)
LOGGER.setLevel(LOG_LEVEL)


async def predict(
    api_key: str,
    username: str,
    report_id: str,
    task_type: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will make the necessary predictions, by training a machine learning
    model on the data provided, and generating predictions needed for the analysis.
    Here are the key steps:

    We will first start by getting the target variable and the features from the
    data, focusing on getting the following correct:
    - type of ML objective (time-series, classification, regression). While time-series
        is a subset of regression, there are some packages that make our life easier
        by handling things like seasonality, change point detection, etc. for us.
    - type of model to use (linear regression, random forest, etc.) based on user
        intent. E.g. If we want to overweight on interpretability, we might choose
        linear regression, if we want to overweight on accuracy, we might choose
        xgboost.
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
    - model_type: type of model generated
    - model_path: path where we save the exported model
    - working:
        - target: name of target variable used
        - features: name of features used
        - unit: unit of prediction used
        - constraints: additional constraints used
    - train_data: csv of training data used
    - predictions: csv of predictions generated

    Side Effects:
    Intermediate model and predictions generated will be saved in the report_id's
    directory.
    """
    LOGGER.info(f"Predicting for report {report_id}")
    ts, timings = time.time(), []
    LOGGER.debug(f"inputs: {inputs}")
    LOGGER.debug(f"outputs:\n{truncate_obj(outputs)}")

    # TODO
    # get the prediction dataframe. we can't reuse the data from the earlier
    # explorer questions as they would get specific views / aggregates for
    # individual feature analysis
    return {"predictions": "predictions generated"}
