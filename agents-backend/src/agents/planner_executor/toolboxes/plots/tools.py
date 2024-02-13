from typing import List
import seaborn as sns
from uuid import uuid4
import matplotlib.pyplot as plt
import pandas as pd

# set default font to Arial
plt.rcParams["font.family"] = "Arial"

available_colors = plt.colormaps()

sns.set_palette(["#009D94", "#0057CF", "#FFBD00", "#FF5C1C", "#691A6B"])

import yaml

from agents.planner_executor.tool_helpers.tool_param_types import (
    DBColumn,
    DropdownSingleSelect,
)

with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

report_assets_dir = env["report_assets_dir"]


def validate_column(df, col_name):
    """
    Checks if a column exists in a dataframe.
    """
    if col_name not in df.columns:
        return False
    return True


async def boxplot(
    full_data: pd.DataFrame,
    boxplot_cols: list[DBColumn],
    facet: bool = False,
    facet_col: DBColumn = None,
    color: DropdownSingleSelect = [
        "#000000",
        "#009D94",
        "#0057CF",
        "#FFBD00",
        "#FF5C1C",
        "#691A6B",
    ],
    opacity: DropdownSingleSelect = [0.1, 0.2, 0.3, 0.4, 0.5],
    global_dict: dict = {},
):
    """
    Generates a boxplot using python's seaborn library. Also accepts faceting columns.
    """
    if len(boxplot_cols) == 1:
        if boxplot_cols[0] == "label":
            new_col = "label_"
        else:
            new_col = "label"
        boxplot_cols = [new_col, boxplot_cols[0]]
        full_data[new_col] = ""

    outputs = []
    boxplot_path = f"boxplots/boxplot-{uuid4()}.png"
    fig, ax = plt.subplots()
    plt.xticks(rotation=45)
    if facet:
        full_data = full_data.dropna(subset=boxplot_cols + [facet_col], how="any")
        # use catplot from seaborn
        g = sns.catplot(
            x=boxplot_cols[0],
            y=boxplot_cols[1],
            data=full_data,
            col=facet_col,
            kind="box",
            col_wrap=4,
        )
        # boxplot with white boxes
        g.map(
            sns.boxplot,
            boxplot_cols[0],
            boxplot_cols[1],
            color="white",
        )
        # add points to the boxplot using stripplot
        # color them black with opacity
        # small size dots
        g.map(
            sns.stripplot, boxplot_cols[0], boxplot_cols[1], color=color, alpha=0.1, s=2
        )
        # save highres with high dpi
        g.figure.savefig(
            f"{report_assets_dir}/{boxplot_path}", dpi=300, bbox_inches="tight"
        )

    else:
        # drop rows with missing values
        full_data = full_data.dropna(subset=boxplot_cols, how="any")
        sns.boxplot(
            x=boxplot_cols[0], y=boxplot_cols[1], data=full_data, ax=ax, color="white"
        )
        sns.stripplot(
            x=boxplot_cols[0],
            y=boxplot_cols[1],
            data=full_data,
            color=color,
            alpha=0.1,
            s=2,
        )
        plt.xticks(rotation=45)
        plt.savefig(f"{report_assets_dir}/{boxplot_path}", dpi=300, bbox_inches="tight")

    plt.close()

    return {
        "outputs": [
            {
                "data": full_data,
                "chart_images": [
                    {
                        "type": "boxplot",
                        "path": boxplot_path,
                    }
                ],
            }
        ],
    }


async def heatmap(
    full_data: pd.DataFrame,
    x_position_column: DBColumn,
    y_position_column: DBColumn,
    color_column: DBColumn,
    # can be mean, median, max, min, or sum
    aggregation_type: DropdownSingleSelect = ["mean", "median", "max", "min", "sum"],
    color_scale: DropdownSingleSelect = available_colors,
    global_dict: dict = {},
):
    """
    Generates a heatmap using python's seaborn library.
    """
    outputs = []
    heatmap_path = f"heatmaps/heatmap-{uuid4()}.png"
    fig, ax = plt.subplots()
    plt.xticks(rotation=45)

    if not aggregation_type or type(aggregation_type) != str:
        raise ValueError("Aggregation type must be a string")

    sns.heatmap(
        full_data.pivot_table(
            index=y_position_column,
            columns=x_position_column,
            values=color_column,
            aggfunc=aggregation_type,
        ),
        annot=True,
        fmt=".1f",
        cmap=color_scale,
        ax=ax,
    )

    plt.savefig(f"{report_assets_dir}/{heatmap_path}", dpi=300, bbox_inches="tight")
    plt.close()

    return {
        "outputs": [
            {
                "data": full_data,
                "chart_images": [
                    {
                        "type": "heatmap",
                        "path": heatmap_path,
                    }
                ],
            }
        ],
    }


async def line_plot(
    full_data: pd.DataFrame,
    x_column: DBColumn,
    y_column: DBColumn,
    hue_column: DBColumn = None,
    facet_col: DBColumn = None,
    estimator: DropdownSingleSelect = ["mean", "median", "max", "min", "sum", "None"],
    units: DBColumn = None,
    global_dict: dict = {},
    **kwargs,
):
    """
    Creates a line plot of the data, using seaborn
    """
    if estimator not in [
        "mean",
        "median",
        "max",
        "min",
        "sum",
        "None",
    ]:
        raise ValueError(
            f"Estimator must was {estimator}, but it must be a string and one of mean, median, max, min, sum, None"
        )

    if estimator == "None":
        estimator = None

    relevant_columns = [x_column, y_column]
    if hue_column:
        relevant_columns.append(hue_column)
    if facet_col:
        relevant_columns.append(facet_col)
    if units:
        relevant_columns.append(units)

    df = full_data.dropna(subset=relevant_columns)

    # sort the dataframe by the x_column
    df = df.sort_values(by=[x_column])

    chart_path = f"linecharts/linechart-{uuid4()}.png"
    fig, ax = plt.subplots()
    plt.xticks(rotation=45)
    # create the plot
    if facet_col is None:
        plot = sns.lineplot(
            data=df[relevant_columns],
            x=x_column,
            y=y_column,
            hue=hue_column,
            estimator=estimator,
            units=units,
        )
    else:
        plot = sns.relplot(
            data=df[relevant_columns],
            x=x_column,
            y=y_column,
            hue=hue_column,
            kind="line",
            col=facet_col,
            estimator=estimator,
            units=units,
        )
    # save the plot
    plot.figure.savefig(
        f"{report_assets_dir}/{chart_path}", dpi=300, bbox_inches="tight"
    )

    plt.close()

    return {
        "outputs": [
            {
                "data": df,
                "chart_images": [
                    {
                        "type": "lineplot",
                        "path": chart_path,
                    }
                ],
            }
        ],
    }
