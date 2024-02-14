from defog import Defog
import pandas as pd
from typing import Tuple

import yaml

with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

report_assets_dir = env["report_assets_dir"]

import traceback
from uuid import uuid4
import numpy as np
from sksurv.preprocessing import OneHotEncoder


from sksurv.nonparametric import kaplan_meier_estimator
from sksurv.datasets import get_x_y
from sksurv.compare import compare_survival
from sksurv.linear_model import CoxPHSurvivalAnalysis
from sklearn.model_selection import GridSearchCV, KFold
import matplotlib.pyplot as plt

from agents.planner_executor.tool_helpers.tool_param_types import (
    DBColumn,
    db_column_list_type_creator,
)


# all of this is stolen from here https://scikit-survival.readthedocs.io/en/stable/user_guide/00-introduction.html
# and here https://www.kaggle.com/code/fciscoalmeida/survival-analysis-in-python
async def kaplan_meier_curve(
    full_data: pd.DataFrame,
    survival_time_col: DBColumn,
    status_col: DBColumn,
    stratification_vars: db_column_list_type_creator(0) = [],
    **kwargs,
):
    """
    This function generates a kaplan meier survival curve using the sksurv library.
    It can be used to generate a survival function for a given survival time column and status column.
    It can also be used to generate a survival function for a given survival time column and status column, stratified by a third column.
    """
    success = False
    error = None
    kmc_plot_path = ""
    outputs = []
    try:
        data_x, data_y = get_x_y(
            full_data,
            attr_labels=[status_col, survival_time_col],
            pos_label=1,
            survival=True,
        )

        if not stratification_vars or len(stratification_vars) == 0:
            kmc_plot_path = f"kaplan-meier-plots/kmc-{uuid4()}.png"
            time, survival_prob, conf_int = kaplan_meier_estimator(
                data_y[status_col], data_y[survival_time_col], conf_type="log-log"
            )

            plt.step(time, survival_prob, where="post")
            plt.fill_between(time, conf_int[0], conf_int[1], alpha=0.25, step="post")
            plt.ylim(0, 1)
            plt.ylabel("est. probability of survival $\hat{S}(t)$")
            plt.xlabel("time $t$")
            plt.savefig(f"{report_assets_dir}/{kmc_plot_path}")
            full_data.kmc_plot_paths = [kmc_plot_path]

            outputs.append(
                {
                    "data": full_data,
                    "chart_images": [{"type": "kmc", "path": kmc_plot_path}],
                }
            )

        else:
            for stratification_var in stratification_vars:
                print("Running stratified analysis on", stratification_var)
                print(data_x.loc[:, stratification_var])
                # create a copy of the full data
                this_data = full_data.copy()
                kmc_plot_path = f"kaplan-meier-plots/kmc-{uuid4()}.png"
                groups = data_x[stratification_var].unique()
                for group in groups:
                    mask = data_x[stratification_var] == group
                    (
                        time_treatment,
                        survival_prob_treatment,
                        conf_int,
                    ) = kaplan_meier_estimator(
                        data_y[status_col][mask],
                        data_y[survival_time_col][mask],
                        conf_type="log-log",
                    )

                    plt.step(
                        time_treatment,
                        survival_prob_treatment,
                        where="post",
                        label=f"{stratification_var} = {group}",
                    )
                    plt.fill_between(
                        time_treatment,
                        conf_int[0],
                        conf_int[1],
                        alpha=0.25,
                        step="post",
                    )

                    plt.ylim(0, 1)
                    plt.ylabel("est. probability of survival $\hat{S}(t)$")
                    plt.xlabel("time $t$")
                    plt.legend(loc="best")
                    plt.savefig(f"{report_assets_dir}/{kmc_plot_path}")

                # this_data.chart_images = [{"type": "kmc", "path": kmc_plot_path}]
                # compare for analysis
                chi2, pvalue = compare_survival(
                    data_y, data_x.loc[:, stratification_var]
                )

                plt.clf()
                plt.close()
                outputs.append(
                    {
                        "data": this_data,
                        "analysis": f"For Kaplan Meier survival function on {stratification_var}: The chi2 statistic is {chi2:.2f} and the p-value is {pvalue:.2f}.\n",
                        "chart_images": [{"type": "kmc", "path": kmc_plot_path}],
                        "reactive_vars": {
                            stratification_var: {
                                "chi2": chi2,
                                "pvalue": pvalue,
                            }
                        },
                    }
                )

        plt.close()
        success = True
    except Exception as e:
        success = False
        plt.clf()
        plt.close()
        print(e)
        traceback.print_exc()
        analysis = ""
        full_data = pd.DataFrame()
        error = e
    finally:
        return {
            "success": success,
            "outputs": outputs,
            "error": error,
        }


# https://scikit-survival.readthedocs.io/en/stable/user_guide/00-introduction.html#Measuring-the-Performance-of-Survival-Models
async def hazard_ratio(
    full_data: pd.DataFrame,
    survival_time_col: DBColumn,
    status_col: DBColumn,
    **kwargs,
):
    """
    This function generates the cox index (hazard ratio) using the sksurv library.
    Investigate which single variable is the best risk predictor. We fit a Cox model to each variable individually and record the c-index on the training set.
    """
    analysis = ""
    success = False
    try:

        def fit_and_score_features(X, y):
            n_features = X.shape[1]
            scores = np.empty(n_features)
            m = CoxPHSurvivalAnalysis()
            for j in range(n_features):
                Xj = X[:, j : j + 1]
                m.fit(Xj, y)
                scores[j] = m.score(Xj, y)
            return scores

        data_x, data_y = get_x_y(
            full_data,
            attr_labels=[status_col, survival_time_col],
            pos_label=1,
            survival=True,
        )
        data_x_numeric = OneHotEncoder().fit_transform(data_x)
        scores = fit_and_score_features(data_x_numeric.values, data_y)
        results = pd.Series(scores, index=data_x_numeric.columns).sort_values(
            ascending=False
        )
        results.name = "c_index"
        results.index.name = "feature"
        results = pd.DataFrame(results).reset_index()

        success = True

    except Exception as e:
        print(e)
        traceback.print_exc()
        full_data = pd.DataFrame()
        success = False
    finally:
        return {"success": success, "outputs": [{"data": results}]}
