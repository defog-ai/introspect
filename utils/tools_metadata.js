export const toolsMetadata = {
  "data_fetcher_and_aggregator": {
    "name": "data_fetcher_and_aggregator",
    "display_name": "Fetch data from database",
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
    "display_name": "Query data from a pandas dataframe",
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
        "default": [
          "mean",
          "median",
          "max",
          "min",
          "sum",
          "None"
        ],
        "type": "DropdownSingleSelect"
      },
      {
        "name": "units",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "plot_average_line",
        "default": [
          "False",
          "True"
        ],
        "type": "DropdownSingleSelect"
      },
      {
        "name": "average_type",
        "default": [
          "mean",
          "median",
          "max",
          "min",
          "mode"
        ],
        "type": "DropdownSingleSelect"
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
        "type": "DBColumnList_0"
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
        "default": [
          "unpaired",
          "paired"
        ],
        "type": "DropdownSingleSelect"
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
        "type": "DBColumnList_1_2"
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
      },
      {
        "name": "color",
        "default": [
          "#000000",
          "#009D94",
          "#0057CF",
          "#FFBD00",
          "#FF5C1C",
          "#691A6B"
        ],
        "type": "DropdownSingleSelect"
      },
      {
        "name": "opacity",
        "default": [
          0.1,
          0.2,
          0.3,
          0.4,
          0.5
        ],
        "type": "DropdownSingleSelect"
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
        "default": [
          "mean",
          "median",
          "max",
          "min",
          "sum"
        ],
        "type": "DropdownSingleSelect"
      },
      {
        "name": "color_scale",
        "default": [
          "magma",
          "inferno",
          "plasma",
          "viridis",
          "cividis",
          "twilight",
          "twilight_shifted",
          "turbo",
          "Blues",
          "BrBG",
          "BuGn",
          "BuPu",
          "CMRmap",
          "GnBu",
          "Greens",
          "Greys",
          "OrRd",
          "Oranges",
          "PRGn",
          "PiYG",
          "PuBu",
          "PuBuGn",
          "PuOr",
          "PuRd",
          "Purples",
          "RdBu",
          "RdGy",
          "RdPu",
          "RdYlBu",
          "RdYlGn",
          "Reds",
          "Spectral",
          "Wistia",
          "YlGn",
          "YlGnBu",
          "YlOrBr",
          "YlOrRd",
          "afmhot",
          "autumn",
          "binary",
          "bone",
          "brg",
          "bwr",
          "cool",
          "coolwarm",
          "copper",
          "cubehelix",
          "flag",
          "gist_earth",
          "gist_gray",
          "gist_heat",
          "gist_ncar",
          "gist_rainbow",
          "gist_stern",
          "gist_yarg",
          "gnuplot",
          "gnuplot2",
          "gray",
          "hot",
          "hsv",
          "jet",
          "nipy_spectral",
          "ocean",
          "pink",
          "prism",
          "rainbow",
          "seismic",
          "spring",
          "summer",
          "terrain",
          "winter",
          "Accent",
          "Dark2",
          "Paired",
          "Pastel1",
          "Pastel2",
          "Set1",
          "Set2",
          "Set3",
          "tab10",
          "tab20",
          "tab20b",
          "tab20c",
          "magma_r",
          "inferno_r",
          "plasma_r",
          "viridis_r",
          "cividis_r",
          "twilight_r",
          "twilight_shifted_r",
          "turbo_r",
          "Blues_r",
          "BrBG_r",
          "BuGn_r",
          "BuPu_r",
          "CMRmap_r",
          "GnBu_r",
          "Greens_r",
          "Greys_r",
          "OrRd_r",
          "Oranges_r",
          "PRGn_r",
          "PiYG_r",
          "PuBu_r",
          "PuBuGn_r",
          "PuOr_r",
          "PuRd_r",
          "Purples_r",
          "RdBu_r",
          "RdGy_r",
          "RdPu_r",
          "RdYlBu_r",
          "RdYlGn_r",
          "Reds_r",
          "Spectral_r",
          "Wistia_r",
          "YlGn_r",
          "YlGnBu_r",
          "YlOrBr_r",
          "YlOrRd_r",
          "afmhot_r",
          "autumn_r",
          "binary_r",
          "bone_r",
          "brg_r",
          "bwr_r",
          "cool_r",
          "coolwarm_r",
          "copper_r",
          "cubehelix_r",
          "flag_r",
          "gist_earth_r",
          "gist_gray_r",
          "gist_heat_r",
          "gist_ncar_r",
          "gist_rainbow_r",
          "gist_stern_r",
          "gist_yarg_r",
          "gnuplot_r",
          "gnuplot2_r",
          "gray_r",
          "hot_r",
          "hsv_r",
          "jet_r",
          "nipy_spectral_r",
          "ocean_r",
          "pink_r",
          "prism_r",
          "rainbow_r",
          "seismic_r",
          "spring_r",
          "summer_r",
          "terrain_r",
          "winter_r",
          "Accent_r",
          "Dark2_r",
          "Paired_r",
          "Pastel1_r",
          "Pastel2_r",
          "Set1_r",
          "Set2_r",
          "Set3_r",
          "tab10_r",
          "tab20_r",
          "tab20b_r",
          "tab20c_r",
          "rocket",
          "rocket_r",
          "mako",
          "mako_r",
          "icefire",
          "icefire_r",
          "vlag",
          "vlag_r",
          "flare",
          "flare_r",
          "crest",
          "crest_r"
        ],
        "type": "DropdownSingleSelect"
      }
    ]
  },
  "fold_change": {
    "name": "fold_change",
    "display_name": "Fold Change",
    "function_signature": [
      {
        "name": "full_data",
        "default": null,
        "type": "pandas.core.frame.DataFrame"
      },
      {
        "name": "value_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "individual_id_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "time_column",
        "default": null,
        "type": "DBColumn"
      },
      {
        "name": "group_column",
        "default": null,
        "type": "DBColumn"
      }
    ]
  }
}