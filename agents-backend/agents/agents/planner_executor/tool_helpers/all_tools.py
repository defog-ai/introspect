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
        "fn": data_fetcher_and_aggregator,
    },
    {
        "name": "dataset_metadata_describer",
        "fn": dataset_metadata_describer,
    },
    {
        "name": "line_plot",
        "fn": line_plot,
    },
    {
        "name": "kaplan_meier_curve",
        "fn": kaplan_meier_curve,
    },
    {
        "name": "hazard_ratio",
        "fn": hazard_ratio,
    },
    {
        "name": "t_test",
        "fn": t_test,
    },
    {
        "name": "anova_test",
        "fn": anova_test,
    },
    {
        "name": "wilcoxon_test",
        "fn": wilcoxon_test,
    },
    {
        "name": "boxplot",
        "fn": boxplot,
    },
    {
        "name": "heatmap",
        "fn": heatmap,
    }
]
