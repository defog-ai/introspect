from defog import Defog
import pandas as pd
from typing import Tuple

from io import StringIO
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt

from agents.planner_executor.tool_helpers.tool_param_types import (
    DBColumn,
    DropdownSingleSelect,
    ListWithDefault,
)

from agents.planner_executor.tool_helpers.sorting_functions import natural_sort
from agents.planner_executor.toolboxes.plots.tools import line_plot


async def dataset_metadata_describer(
    global_dict={}, **kwargs
) -> Tuple[str, pd.DataFrame]:
    print(global_dict.get("table_metadata_csv"))
    temp_df = pd.read_csv(StringIO(global_dict.get("table_metadata_csv"), ""))
    temp_df = temp_df[["column_name", "data_type", "column_description"]]
    print(temp_df)
    return {
        "outputs": [{"data": temp_df}],
    }


async def t_test(
    full_data: pd.DataFrame,
    group_column: DBColumn,
    score_column: DBColumn,
    name_column: DBColumn,
    t_test_type: DropdownSingleSelect = ListWithDefault(
        ["unpaired", "paired"], default_value="unpaired"
    ),
    global_dict: dict = {},
    **kwargs,
) -> Tuple[str, pd.DataFrame]:
    """
    This function gets two samples and runs a t-test to check if there is a significant difference between their means.
    There are two ways to run the test: paired and unpaired.
    """

    print(group_column)
    print(score_column)
    reactive_vars = {}

    if name_column == "" or name_column is None:
        subset_columns = [group_column, score_column]
    else:
        subset_columns = [group_column, score_column, name_column]

    df = full_data.dropna(subset=subset_columns)
    # TODO add error handling for when there are not enough rows
    # get the two samples
    # next, ensure that the cumulative number of groups for the group_columns is 2

    groups = df[group_column].unique().tolist()
    print(groups)

    # if there are more than 2 groups, we can't run t tests, so return an error
    if len(groups) > 2:
        return {
            "error_message": "More than 2 groups. Consider running ANOVA or Wilcoxon test."
        }

    # run an unpaired t-test
    if t_test_type == "unpaired":
        # now find all the groups and values
        samples = []
        for group_name in groups:
            sample = df[df[group_column] == group_name]
            sample.name = group_name
            samples.append(sample)

        sample1 = samples[0]
        sample2 = samples[1]

        # now we have all the samples, we can run the t test
        sample_1_values = sample1[score_column]
        sample_2_values = sample2[score_column]

        statistic, p_value = stats.ttest_ind(sample_1_values, sample_2_values)

        analysis = f"t-test between:\nSample 1: {sample1.name}\nSample 2: {sample2.name}\nstatistic: {statistic:.4f}\np-value: {p_value:.4f}"
        if p_value < 0.05:
            significance = "a"
            direction = "positive " if statistic > 0 else "negative "
        else:
            significance = "no"
            direction = ""
        analysis += f"\nThere is {significance} significant {direction}difference between the means of {sample1.name} and {sample2.name}."
        # save statistic and p_value into a dataframe
        reactive_vars = {
            "unpaired t-test": {
                "statistic": statistic,
                "p_value": p_value,
            }
        }
        t_test_df = pd.DataFrame(
            {
                "test_type": ["unpaired t-test"],
                "statistic": [statistic],
                "p_value": [p_value],
            }
        )
    else:
        # run a paired t-test
        sample_1 = df[df[group_column] == groups[0]][score_column]
        sample_1.name = groups[0]
        sample_2 = df[df[group_column] == groups[1]][score_column]
        sample_2.name = groups[1]

        sample_1 = sample_1.set_index(name_column)
        sample_2 = sample_2.set_index(name_column)

        # combine the two samples into one dataframe, with name_col as the index and score_columns as the column
        combined_df = sample_1.join(sample_2, lsuffix="_1", rsuffix="_2")
        combined_df = combined_df.dropna()

        # use scipy.stats.ttest_rel for paired t-test
        statistic, p_value = stats.ttest_rel(
            combined_df[combined_df.columns[0]], combined_df[combined_df.columns[1]]
        )

        analysis = f"Paired t-test between:\nSample 1: {sample_1.name}\nSample 2: {sample_2.name}\nstatistic: {statistic:.4f}\np-value: {p_value:.4f}"
        if p_value < 0.05:
            significance = "a"
            direction = "positive " if statistic > 0 else "negative "
        else:
            significance = "no"
            direction = ""
        analysis += f"\nThere is {significance} significant {direction}difference between the means of {sample_1.name} and {sample_2.name}."
        # save statistic and p_value into a dataframe
        reactive_vars = {
            "paired t-test": {
                "statistic": statistic,
                "p_value": p_value,
            }
        }
        t_test_df = pd.DataFrame(
            {
                "test_type": ["paired t-test"],
                "statistic": [statistic],
                "p_value": [p_value],
            }
        )

    t_test_df.reactive_vars = reactive_vars
    return {
        "outputs": [
            {
                "data": t_test_df,
                "reactive_vars": reactive_vars,
                "analysis": analysis,
            }
        ],
    }


async def wilcoxon_test(
    full_data: pd.DataFrame,
    group_column: DBColumn,
    score_column: DBColumn,
    name_column: DBColumn,
    global_dict: dict = {},
    **kwargs,
):
    """
    This function gets two samples and runs a wilcoxon test to check if there is a significant difference between their means.
    """
    df = full_data.dropna()
    group_name_1, group_name_2 = df[group_column].unique().tolist()

    sample_1 = df[df[group_column] == group_name_1][score_column]
    sample_1.name = group_name_1
    sample_2 = df[df[group_column] == group_name_2][score_column]
    sample_2.name = group_name_2

    sample_1 = sample_1.set_index(name_column)
    sample_2 = sample_2.set_index(name_column)

    # combine the two samples into one dataframe, with name_col as the index and score_columns as the column
    combined_df = sample_1.join(sample_2, lsuffix="_1", rsuffix="_2")
    combined_df = combined_df.dropna()

    # run a wilcoxon test
    statistic, p_value, z_statistic = stats.wilcoxon(
        combined_df[combined_df.columns[0]], sample_2[combined_df.columns[1]]
    )
    analysis = f"Wilcoxon test between:\nSample 1: {sample_1.name}\nSample 2: {sample_2.name}\nstatistic: {statistic:.4f}\np-value: {p_value:.4f}\nz-statistic: {z_statistic:.4f}"
    if p_value < 0.05:
        significance = "a"
        direction = "positive " if statistic > 0 else "negative "
    else:
        significance = "no"
        direction = ""
    analysis += f"\nThere is {significance} significant {direction}difference between the means of {sample_1.name} and {sample_2.name}."
    # save statistic and p_value into a dataframe
    reactive_vars = {
        "wilcoxon test": {
            "statistic": statistic,
            "p_value": p_value,
            "z_statistic": z_statistic,
        }
    }
    wilcoxon_df = pd.DataFrame(
        {
            "test_type": ["wilcoxon test"],
            "statistic": [statistic],
            "p_value": [p_value],
            "z_statistic": [z_statistic],
        }
    )
    wilcoxon_df.reactive_vars = reactive_vars
    return {
        "outputs": [
            {
                "data": wilcoxon_df,
                "reactive_vars": reactive_vars,
                "analysis": analysis,
            }
        ],
    }


async def anova_test(
    full_data: pd.DataFrame,
    group_column: DBColumn,
    score_column: DBColumn,
    global_dict: dict = {},
    **kwargs,
):
    """
    This function gets multple samples and runs an ANOVA test to check if there is a significant difference between their means.
    """
    df = full_data.dropna(subset=[group_column, score_column])

    # run an ANOVA test
    import statsmodels
    from statsmodels.stats.oneway import anova_oneway

    res = anova_oneway(
        df[score_column], df[group_column], use_var="unequal", welch_correction=True
    )

    statistic, pvalue = res
    analysis = f"ANOVA test between:\nGroups: {df[group_column].unique().tolist()}\nstatistic: {statistic:.4f}\np-value: {pvalue:.4f}\n"
    if pvalue < 0.05:
        significance = "a"
        direction = "positive " if statistic > 0 else "negative "
    else:
        significance = "no"
        direction = ""
    analysis += f"\nThere is {significance} significant {direction}difference between the means of the groups."

    # save statistic and p_value into a dataframe
    reactive_vars = {
        "ANOVA test": {
            "statistic": statistic,
            "p_value": pvalue,
        }
    }
    anova_df = pd.DataFrame(
        {
            "test_type": ["ANOVA test"],
            "statistic": [statistic],
            "p_value": [pvalue],
        }
    )
    anova_df.reactive_vars = reactive_vars
    return {
        "outputs": [
            {
                "data": anova_df,
                "reactive_vars": reactive_vars,
                "analysis": analysis,
            }
        ],
    }


async def fold_change(
    full_data: pd.DataFrame,
    value_column: DBColumn,
    individual_id_column: DBColumn,
    time_column: DBColumn,
    group_column: DBColumn = None,
    global_dict: dict = {},
):
    """
    This function calculates the fold change between two groups of values.
    """
    df = full_data.dropna(subset=[value_column, individual_id_column, time_column])

    if group_column is not None:
        id_group = (
            df.dropna(subset=[individual_id_column, group_column])
            .set_index(individual_id_column)[group_column]
            .to_dict()
        )
    if len(df) == 0:
        return {"error_message": "No data to calculate fold change."}

    df = (
        df.groupby([individual_id_column, time_column])[value_column]
        .mean()
        .reset_index()
    )
    df = natural_sort(df, time_column, individual_id_column)

    # calculate the fold change for each group, which is the ratio of the value in first time_column to the value in a given time_column
    fold_change_df = df.pivot(
        index=time_column, columns=individual_id_column, values=value_column
    )
    fold_change_df = fold_change_df / fold_change_df.iloc[0]
    # fold_change_df = fold_change_df.dropna(how="all", axis=1).reset_index()

    # unpivot the dataframe
    fold_change_df = fold_change_df.reset_index()
    fold_change_df_melted = fold_change_df.melt(
        id_vars=[time_column], var_name=individual_id_column, value_name="fold_change"
    )

    # plot charts – we always want to create a line chart here
    fold_change_df_melted = natural_sort(
        fold_change_df_melted, time_column, individual_id_column
    )

    if group_column is not None:
        fold_change_df_melted[group_column] = fold_change_df_melted[
            individual_id_column
        ].map(id_group.get)

    # plot the fold change
    resp = await line_plot(
        fold_change_df_melted,
        time_column,
        "fold_change",
        units=individual_id_column,
        facet_col=group_column,
    )
    return {
        "outputs": [
            {
                "data": fold_change_df,
                "chart_images": [
                    {
                        "type": "lineplot",
                        "path": resp["outputs"][0]["chart_images"][0]["path"],
                    }
                ],
            }
        ],
    }
