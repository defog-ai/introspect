# this is where you can import your custom tools
# create a folder insider toolboxes and add your tools (aka python functions) there inside a tools.py file
# and finally add all your tools in the tools array below in the given format
from ..toolboxes.data_fetching.tools import *
from ..toolboxes.stats.tools import *
from ..toolboxes.cancer_survival.tools import *
from ..toolboxes.plots.tools import *


tools = [
    {
        "name": "data_fetcher_and_aggregator",
        "display_name": "Data Fetcher and Aggregator",
        "fn": data_fetcher_and_aggregator,
        "no_code": True,
    },
    {
        "name": "global_dict_data_fetcher_and_aggregator",
        "display_name": "Global Dict Data Fetcher and Aggregator",
        "fn": global_dict_data_fetcher_and_aggregator,
        "no_code": True,
    },
    {
        "name": "dataset_metadata_describer",
        "display_name": "Dataset Metadata Describer",
        "fn": dataset_metadata_describer,
    },
    {
        "name": "line_plot",
        "display_name": "Line Plot",
        "fn": line_plot,
    },
    {
        "name": "kaplan_meier_curve",
        "display_name": "Kaplan Meier Curve",
        "fn": kaplan_meier_curve,
    },
    {
        "name": "hazard_ratio",
        "display_name": "Hazard Ratio",
        "fn": hazard_ratio,
    },
    {
        "name": "t_test",
        "display_name": "T Test",
        "fn": t_test,
    },
    {
        "name": "anova_test",
        "display_name": "ANOVA Test",
        "fn": anova_test,
    },
    {
        "name": "wilcoxon_test",
        "display_name": "Wilcoxon Test",
        "fn": wilcoxon_test,
    },
    {
        "name": "boxplot",
        "display_name": "Boxplot",
        "fn": boxplot,
    },
    {
        "name": "heatmap",
        "display_name": "Heatmap",
        "fn": heatmap,
    },
]

tool_name_dict = {tool["name"]: tool for tool in tools}
