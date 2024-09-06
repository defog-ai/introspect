from tool_code_utilities import available_colors

import seaborn as sns

sns.set_palette(["#009D94", "#FF5C1C", "#0057CF", "#691A6B", "#FFBD00"])
import pandas as pd

from agents.planner_executor.tool_helpers.tool_param_types import (
    DBColumn,
    DropdownSingleSelect,
    ListWithDefault,
    db_column_list_type_creator,
)

import yaml


def validate_column(df, col_name):
    """
    Checks if a column exists in a dataframe.
    """
    if col_name not in df.columns:
        return False
    return True


async def boxplot(
    full_data: pd.DataFrame,
    x_column: DBColumn,
    y_column: DBColumn,
    facet: bool = False,
    facet_column: DBColumn = None,
    color: DropdownSingleSelect = ListWithDefault(
        [
            "#000000",
            "#009D94",
            "#0057CF",
            "#FFBD00",
            "#FF5C1C",
            "#691A6B",
        ],
        default_value="#000000",
    ),
    opacity: DropdownSingleSelect = ListWithDefault(
        [0.1, 0.2, 0.3, 0.4, 0.5], default_value=0.3
    ),
    global_dict: dict = {},
):
    """
    Generates a boxplot using python's seaborn library. Also accepts faceting columns.
    """
    import seaborn as sns
    from uuid import uuid4
    import matplotlib.pyplot as plt
    import pandas as pd

    # if there's not an index column, create one
    if "index" not in full_data.columns:
        full_data["index"] = range(len(full_data))

    analysis_assets_dir = global_dict.get(
        "analysis_assets_dir", "/agents-assets/analysis-assets"
    )

    if type(color) == ListWithDefault:
        color = color.default_value

    if not color:
        color = "#000000"

    if type(color) != str:
        # support for versions before we had the ListWithDefault class
        color = "#000000"

    if type(opacity) == ListWithDefault:
        opacity = opacity.default_value

    if not opacity or type(opacity) != float:
        # support for versions before we had the ListWithDefault class
        opacity = 0.3

    # if any of x or y column is None, set that to "label" and create a new column "label" with empty string
    if x_column is None:
        x_column = "label"
        full_data["label"] = ""
    if y_column is None:
        y_column = "label"
        # in this case, we don't want a label column to be on the y axis
        # but on the x axis
        # so we will swap the x and y columns
        x_column, y_column = y_column, x_column
        full_data["label"] = ""

    outputs = []
    boxplot_path = f"boxplots/boxplot-{uuid4()}.png"
    fig, ax = plt.subplots()
    plt.xticks(rotation=45)
    if facet:
        full_data = full_data.dropna(
            subset=[x_column, y_column] + [facet_column], how="any"
        )
        # use catplot from seaborn
        g = sns.catplot(
            x=x_column,
            y=y_column,
            data=full_data,
            col=facet_column,
            kind="box",
            col_wrap=4,
            fill=False,
        )
        # boxplot with white boxes
        g.map(
            sns.boxplot,
            x_column,
            y_column,
            color=color,
            fill=False,
        )
        # add points to the boxplot using stripplot
        # color them black with opacity
        # small size dots
        g.map(
            sns.stripplot,
            x_column,
            y_column,
            color=color,
            alpha=opacity,
            s=2,
        )
        plt.xticks(rotation=45)

        # save highres with high dpi
        g.figure.savefig(
            f"{analysis_assets_dir}/{boxplot_path}", dpi=300, bbox_inches="tight"
        )

    else:
        # drop rows with missing values
        full_data = full_data.dropna(
            subset=[x_column, y_column], how="any"
        )
        sns.boxplot(
            x=x_column,
            y=y_column,
            data=full_data,
            ax=ax,
            color=color,
            fill=False,
        )
        sns.stripplot(
            x=x_column,
            y=y_column,
            data=full_data,
            color=color,
            alpha=opacity,
            s=2,
        )
        plt.xticks(rotation=45)
        plt.savefig(
            f"{analysis_assets_dir}/{boxplot_path}", dpi=300, bbox_inches="tight"
        )

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
    x_column: DBColumn,
    y_column: DBColumn,
    color_column: DBColumn,
    # can be mean, median, max, min, or sum
    aggregation_type: DropdownSingleSelect = ListWithDefault(
        ["mean", "median", "max", "min", "sum"], default_value="mean"
    ),
    color_scale: DropdownSingleSelect = ListWithDefault(
        available_colors, default_value="viridis"
    ),
    global_dict: dict = {},
):
    """
    Generates a heatmap using python's seaborn library.
    """
    import seaborn as sns
    from uuid import uuid4
    import matplotlib.pyplot as plt
    import pandas as pd

    # if there's not an index column, create one
    if "index" not in full_data.columns:
        full_data["index"] = range(len(full_data))

    outputs = []
    heatmap_path = f"heatmaps/heatmap-{uuid4()}.png"
    fig, ax = plt.subplots()
    plt.xticks(rotation=45)
    analysis_assets_dir = global_dict.get(
        "analysis_assets_dir", "/agents-assets/analysis-assets"
    )

    if not aggregation_type or type(aggregation_type) != str:
        raise ValueError("Aggregation type must be a string")

    if type(color_scale) == ListWithDefault:
        color_scale = color_scale.default_value

    sns.heatmap(
        full_data.pivot_table(
            index=y_column,
            columns=x_column,
            values=color_column,
            aggfunc=aggregation_type,
        ),
        annot=True,
        fmt=".1f",
        cmap=color_scale,
        ax=ax,
    )

    plt.savefig(f"{analysis_assets_dir}/{heatmap_path}", dpi=300, bbox_inches="tight")
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
    color_column: DBColumn = None,
    facet_column: DBColumn = None,
    line_group_column: DBColumn = None,
    aggregation_type: DropdownSingleSelect = ListWithDefault(
        ["mean", "median", "max", "min", "sum", "None"], default_value=None
    ),
    plot_average_line: DropdownSingleSelect = ListWithDefault(
        ["False", "True"], default_value=None
    ),
    # the kind of value for the average line to have. Can be mean, median, max, min, or mode. None if no average line required"
    average_line_type: DropdownSingleSelect = ListWithDefault(
        ["mean", "median", "max", "min", "mode"], default_value=None
    ),
    global_dict: dict = {},
    **kwargs,
):
    """
    Creates a line plot of the data, using seaborn
    """
    from tool_code_utilities import natural_sort
    import seaborn as sns
    from uuid import uuid4
    import matplotlib.pyplot as plt

    # if there's not an index column, create one
    if "index" not in full_data.columns:
        full_data["index"] = range(len(full_data))

    analysis_assets_dir = global_dict.get(
        "analysis_assets_dir", "/agents-assets/analysis-assets"
    )

    if type(average_line_type) == ListWithDefault:
        average_line_type = average_line_type[0]

    if type(plot_average_line) == ListWithDefault:
        plot_average_line = plot_average_line[0]

    if type(aggregation_type) == ListWithDefault:
        aggregation_type = aggregation_type[0]

    if aggregation_type is None:
        aggregation_type = "None"

    if facet_column == color_column:
        color_column = None

    if aggregation_type not in [
        "mean",
        "median",
        "max",
        "min",
        "sum",
        "None",
    ]:
        raise ValueError(
            f"aggregation_type must was {aggregation_type}, but it must be a string and one of mean, median, max, min, sum, None"
        )

    if aggregation_type == "None":
        aggregation_type = None

    if line_group_column:
        aggregation_type = None

    # if x_column is a numerical value and y_column is a string, swap them
    if full_data[x_column].dtype != "object" and full_data[y_column].dtype == "object":
        x_column, y_column = y_column, x_column

    relevant_columns = [x_column, y_column]
    if color_column:
        relevant_columns.append(color_column)
    if facet_column:
        relevant_columns.append(facet_column)
    if line_group_column:
        relevant_columns.append(line_group_column)

    df = full_data.dropna(subset=relevant_columns)[relevant_columns]

    if line_group_column is not None:
        df = (
            df.groupby([i for i in relevant_columns if i != y_column])[y_column]
            .mean()
            .reset_index()
        )

    # sort the dataframe by the x_column
    df = natural_sort(df, x_column, line_group_column)

    chart_path = f"linecharts/linechart-{uuid4()}.png"
    fig, ax = plt.subplots()
    plt.xticks(rotation=45)

    if line_group_column:
        linewidth = 0.75
    else:
        linewidth = 1

    # create the plot
    if facet_column is None:
        plot = sns.lineplot(
            data=df[relevant_columns],
            x=x_column,
            y=y_column,
            hue=color_column,
            estimator=aggregation_type,
            # line_group_column=line_group_column,
            linewidth=linewidth,
        )
        # Calculating the median value of 'y'
        if average_line_type == "median":
            value_to_plot = df[y_column].median()
        elif average_line_type == "mean":
            value_to_plot = df[y_column].mean()
        elif average_line_type == "max":
            value_to_plot = df[y_column].max()
        elif average_line_type == "min":
            value_to_plot = df[y_column].min()
        elif average_line_type == "mode":
            value_to_plot = df[y_column].mode()

        # Adding a horizontal line for the median value
        if plot_average_line == "True":
            plt.axhline(
                y=value_to_plot,
                color="k",
                linestyle="--",
                label=f"{average_line_type.title()}: {value_to_plot:.2f}",
                linewidth=2,
            )

        plt.xticks(rotation=45)
    else:
        plot = sns.relplot(
            data=df[relevant_columns],
            x=x_column,
            y=y_column,
            hue=color_column,
            kind="line",
            col=facet_column,
            estimator=aggregation_type,
            # line_group_column=line_group_column,
            col_wrap=4,
            linewidth=linewidth,
        )

        for group, ax in plot.axes_dict.items():
            if average_line_type == "median":
                value_to_plot = df[df[facet_column] == group][y_column].median()
            elif average_line_type == "mean":
                value_to_plot = df[df[facet_column] == group][y_column].mean()
            elif average_line_type == "max":
                value_to_plot = df[df[facet_column] == group][y_column].max()
            elif average_line_type == "min":
                value_to_plot = df[df[facet_column] == group][y_column].min()
            elif average_line_type == "mode":
                value_to_plot = df[df[facet_column] == group][y_column].mode()
            if plot_average_line == "True":
                ax.axhline(
                    y=value_to_plot,
                    color="k",
                    linestyle="--",
                    label=f"{average_line_type.title()}: {value_to_plot:.2f}",
                    linewidth=2,
                )
            try:
                plot.xticks(rotation=45)
            except Exception as e:
                print(str(e), flush=True)
                print("Error in rotating xticks", flush=True)

    plt.xticks(rotation=45)

    # save the plot
    plot.figure.savefig(
        f"{analysis_assets_dir}/{chart_path}", dpi=300, bbox_inches="tight"
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
