from typing import List
import seaborn as sns
from uuid import uuid4
import matplotlib.pyplot as plt
import pandas as pd

# set default font to Arial
# TODO: enable this after figuring out how to install Arial font inside Docker
# plt.rcParams["font.family"] = "Arial"

available_colors = plt.colormaps()

sns.set_palette(["#009D94", "#FF5C1C", "#0057CF", "#691A6B", "#FFBD00"])

import yaml

from agents.planner_executor.tool_helpers.tool_param_types import (
    DBColumn,
    DropdownSingleSelect,
    db_column_list_type_creator,
)
from agents.planner_executor.tool_helpers.sorting_functions import natural_sort

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
    boxplot_cols: db_column_list_type_creator(1, 2),
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

    if type(color) == list:
        color = color[0]

    if not color or type(color) != str:
        raise ValueError("Color must be a string")

    if type(opacity) == list:
        opacity = opacity[0]

    if not opacity or type(opacity) != float:
        raise ValueError("Opacity must be a float")

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
            fill=False,
        )
        # boxplot with white boxes
        g.map(
            sns.boxplot,
            boxplot_cols[0],
            boxplot_cols[1],
            color=color,
            fill=False,
        )
        # add points to the boxplot using stripplot
        # color them black with opacity
        # small size dots
        g.map(
            sns.stripplot,
            boxplot_cols[0],
            boxplot_cols[1],
            color=color,
            alpha=opacity,
            s=2,
        )
        plt.xticks(rotation=45)

        # save highres with high dpi
        g.figure.savefig(
            f"{report_assets_dir}/{boxplot_path}", dpi=300, bbox_inches="tight"
        )

    else:
        # drop rows with missing values
        full_data = full_data.dropna(subset=boxplot_cols, how="any")
        sns.boxplot(
            x=boxplot_cols[0],
            y=boxplot_cols[1],
            data=full_data,
            ax=ax,
            color=color,
            fill=False,
        )
        sns.stripplot(
            x=boxplot_cols[0],
            y=boxplot_cols[1],
            data=full_data,
            color=color,
            alpha=opacity,
            s=2,
        )
        plt.xticks(rotation=45)
        plt.savefig(f"{report_assets_dir}/{boxplot_path}", dpi=300, bbox_inches="tight")

    plt.clf()
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
    plt.clf()
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
    plot_average_line: DropdownSingleSelect = ["False", "True"],
    average_type: DropdownSingleSelect = ["mean", "median", "max", "min", "mode"],
    global_dict: dict = {},
    **kwargs,
):
    """
    Creates a line plot of the data, using seaborn
    """
    if type(average_type) == list:
        average_type = average_type[0]

    if type(plot_average_line) == list:
        plot_average_line = plot_average_line[0]

    if type(estimator) == list:
        estimator = estimator[0]

    if estimator is None:
        estimator = "None"

    if facet_col == hue_column:
        hue_column = None

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

    if units:
        estimator = None

    # if x_column is a numerical value and y_column is a string, swap them
    if full_data[x_column].dtype != "object" and full_data[y_column].dtype == "object":
        x_column, y_column = y_column, x_column

    relevant_columns = [x_column, y_column]
    if hue_column:
        relevant_columns.append(hue_column)
    if facet_col:
        relevant_columns.append(facet_col)
    if units:
        relevant_columns.append(units)

    df = full_data.dropna(subset=relevant_columns)[relevant_columns]

    if units is not None:
        df = (
            df.groupby([i for i in relevant_columns if i != y_column])[y_column]
            .mean()
            .reset_index()
        )

    # sort the dataframe by the x_column
    df = natural_sort(df, x_column, units)

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
        # Calculating the median value of 'y'
        if average_type == "median":
            value_to_plot = df[y_column].median()
        elif average_type == "mean":
            value_to_plot = df[y_column].mean()
        elif average_type == "max":
            value_to_plot = df[y_column].max()
        elif average_type == "min":
            value_to_plot = df[y_column].min()
        elif average_type == "mode":
            value_to_plot = df[y_column].mode()

        # Adding a horizontal line for the median value
        if plot_average_line == "True":
            plt.axhline(
                y=value_to_plot,
                color="r",
                linestyle="--",
                label=f"{average_type.title()}: {value_to_plot:.2f}",
            )

        plt.xticks(rotation=45)
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
            col_wrap=4,
        )

        for group, ax in plot.axes_dict.items():
            if average_type == "median":
                value_to_plot = df[df[facet_col] == group][y_column].median()
            elif average_type == "mean":
                value_to_plot = df[df[facet_col] == group][y_column].mean()
            elif average_type == "max":
                value_to_plot = df[df[facet_col] == group][y_column].max()
            elif average_type == "min":
                value_to_plot = df[df[facet_col] == group][y_column].min()
            elif average_type == "mode":
                value_to_plot = df[df[facet_col] == group][y_column].mode()
            if plot_average_line == "True":
                ax.axhline(
                    y=value_to_plot,
                    color="r",
                    linestyle="--",
                    label=f"{average_type.title()}: {value_to_plot:.2f}",
                )
            try:
                plot.xticks(rotation=45)
            except:
                print("Error in rotating xticks")

    plt.xticks(rotation=45)

    # save the plot
    plot.figure.savefig(
        f"{report_assets_dir}/{chart_path}", dpi=300, bbox_inches="tight"
    )
    plt.clf()
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
