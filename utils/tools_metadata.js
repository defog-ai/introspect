export const toolsMetadata = {
  "data_fetcher_and_aggregator": {
    "name": "data_fetcher_and_aggregator",
    "display_name": "Data Fetcher and Aggregator",
    "function_signature": [
      {
        "name": "question",
        "default": null,
        "type": "str"
      }
    ]
  },
  "global_dict_data_fetcher_and_aggregator": {
    "name": "global_dict_data_fetcher_and_aggregator",
    "display_name": "Global Dict Data Fetcher and Aggregator",
    "function_signature": [
      {
        "name": "question",
        "default": null,
        "type": "str"
      },
      {
        "name": "input_df",
        "default": null,
        "type": "pandas.core.frame.DataFrame"
      }
    ]
  },
  "dataset_metadata_describer": {
    "name": "dataset_metadata_describer",
    "display_name": "Dataset Metadata Describer",
    "function_signature": []
  },
  "line_plot": {
    "name": "line_plot",
    "display_name": "Line Plot",
    "function_signature": [
      {
        "name": "full_data",
        "default": null,
        "type": "pandas.core.frame.DataFrame"
      },
      {
        "name": "x_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "y_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "hue_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "facet_col",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "estimator",
        "default": "mean",
        "type": "str"
      },
      {
        "name": "units",
        "default": null,
        "type": "str"
      }
    ]
  },
  "kaplan_meier_curve": {
    "name": "kaplan_meier_curve",
    "display_name": "Kaplan Meier Curve",
    "function_signature": [
      {
        "name": "full_data",
        "default": null,
        "type": "pandas.core.frame.DataFrame"
      },
      {
        "name": "survival_time_col",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "status_col",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "stratification_vars",
        "default": [],
        "type": "list[DBColumn]"
      }
    ]
  },
  "hazard_ratio": {
    "name": "hazard_ratio",
    "display_name": "Hazard Ratio",
    "function_signature": [
      {
        "name": "full_data",
        "default": null,
        "type": "pandas.core.frame.DataFrame"
      },
      {
        "name": "survival_time_col",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "status_col",
        "default": null,
        "type": "DBColumn"
      }
    ]
  },
  "t_test": {
    "name": "t_test",
    "display_name": "T Test",
    "function_signature": [
      {
        "name": "full_data",
        "default": null,
        "type": "pandas.core.frame.DataFrame"
      },
      {
        "name": "group_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "score_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "name_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "t_test_type",
        "default": "unpaired",
        "type": "str"
      }
    ]
  },
  "anova_test": {
    "name": "anova_test",
    "display_name": "ANOVA Test",
    "function_signature": [
      {
        "name": "full_data",
        "default": null,
        "type": "pandas.core.frame.DataFrame"
      },
      {
        "name": "group_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "score_column",
        "default": null,
        "type": "DBColumn"
      }
    ]
  },
  "wilcoxon_test": {
    "name": "wilcoxon_test",
    "display_name": "Wilcoxon Test",
    "function_signature": [
      {
        "name": "full_data",
        "default": null,
        "type": "pandas.core.frame.DataFrame"
      },
      {
        "name": "group_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "score_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "name_column",
        "default": null,
        "type": "DBColumn"
      }
    ]
  },
  "boxplot": {
    "name": "boxplot",
    "display_name": "Boxplot",
    "function_signature": [
      {
        "name": "full_data",
        "default": null,
        "type": "pandas.core.frame.DataFrame"
      },
      {
        "name": "boxplot_cols",
        "default": null,
        "type": "list[DBColumn]"
      },
      {
        "name": "facet",
        "default": false,
        "type": "bool"
      },
      {
        "name": "facet_col",
        "default": null,
        "type": "DBColumn"
      }
    ]
  },
  "heatmap": {
    "name": "heatmap",
    "display_name": "Heatmap",
    "function_signature": [
      {
        "name": "full_data",
        "default": null,
        "type": "pandas.core.frame.DataFrame"
      },
      {
        "name": "x_position_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "y_position_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "color_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "aggregation_type",
        "default": "mean",
        "type": "str"
      },
      {
        "name": "color_scale",
        "default": "YlGnBu",
        "type": "str"
      }
    ]
  }
}