export const toolsMetadata = {
  data_fetcher_and_aggregator: {
    name: "data_fetcher_and_aggregator",
    display_name: "Data Fetcher and Aggregator",
    function_signature: [
      {
        name: "question",
        default: null,
        type: "str",
      },
    ],
  },
  global_dict_data_fetcher_and_aggregator: {
    name: "global_dict_data_fetcher_and_aggregator",
    display_name: "Query Data",
    function_signature: [
      {
        name: "question",
        default: null,
        type: "str",
      },
      {
        name: "input_df",
        default: null,
        type: "pandas.core.frame.DataFrame",
      },
    ],
  },
  dataset_metadata_describer: {
    name: "dataset_metadata_describer",
    display_name: "Dataset Metadata Describer",
    function_signature: [],
  },
  line_plot: {
    name: "line_plot",
    display_name: "Line Plot",
    function_signature: [
      {
        name: "full_data",
        default: null,
        type: "pandas.core.frame.DataFrame",
      },
      {
        name: "x_column",
        default: null,
        type: "str",
      },
      {
        name: "y_column",
        default: null,
        type: "str",
      },
      {
        name: "hue_column",
        default: null,
        type: "str",
      },
      {
        name: "facet_col",
        default: null,
        type: "str",
      },
      {
        name: "estimator",
        default: "mean",
        type: "str",
      },
    ],
  },
  kaplan_meier_curve: {
    name: "kaplan_meier_curve",
    display_name: "Kaplan Meier Curve",
    function_signature: [
      {
        name: "full_data",
        default: null,
        type: "pandas.core.frame.DataFrame",
      },
      {
        name: "survival_time_col",
        default: null,
        type: "str",
      },
      {
        name: "status_col",
        default: null,
        type: "str",
      },
      {
        name: "stratification_vars",
        default: null,
        type: "list",
      },
    ],
  },
  hazard_ratio: {
    name: "hazard_ratio",
    display_name: "Hazard Ratio",
    function_signature: [
      {
        name: "full_data",
        default: null,
        type: "pandas.core.frame.DataFrame",
      },
      {
        name: "survival_time_col",
        default: null,
        type: "str",
      },
      {
        name: "status_col",
        default: null,
        type: "str",
      },
    ],
  },
  t_test: {
    name: "t_test",
    display_name: "T Test",
    function_signature: [
      {
        name: "full_data",
        default: null,
        type: "pandas.core.frame.DataFrame",
      },
      {
        name: "group_column",
        default: null,
        type: "str",
      },
      {
        name: "score_column",
        default: null,
        type: "str",
      },
      {
        name: "name_column",
        default: null,
        type: "str",
      },
      {
        name: "t_test_type",
        default: "unpaired",
        type: "str",
      },
    ],
  },
  anova_test: {
    name: "anova_test",
    display_name: "ANOVA Test",
    function_signature: [
      {
        name: "full_data",
        default: null,
        type: "pandas.core.frame.DataFrame",
      },
      {
        name: "group_column",
        default: null,
        type: "str",
      },
      {
        name: "score_column",
        default: null,
        type: "str",
      },
    ],
  },
  wilcoxon_test: {
    name: "wilcoxon_test",
    display_name: "Wilcoxon Test",
    function_signature: [
      {
        name: "full_data",
        default: null,
        type: "pandas.core.frame.DataFrame",
      },
      {
        name: "group_column",
        default: null,
        type: "str",
      },
      {
        name: "score_column",
        default: null,
        type: "str",
      },
      {
        name: "name_column",
        default: null,
        type: "str",
      },
    ],
  },
  boxplot: {
    name: "boxplot",
    display_name: "Boxplot",
    function_signature: [
      {
        name: "full_data",
        default: null,
        type: "pandas.core.frame.DataFrame",
      },
      {
        name: "boxplot_cols",
        default: null,
        type: "list",
      },
      {
        name: "facet",
        default: false,
        type: "bool",
      },
      {
        name: "facet_col",
        default: "",
        type: "str",
      },
    ],
  },
  heatmap: {
    name: "heatmap",
    display_name: "Heatmap",
    function_signature: [
      {
        name: "full_data",
        default: null,
        type: "pandas.core.frame.DataFrame",
      },
      {
        name: "x_position_column",
        default: null,
        type: "str",
      },
      {
        name: "y_position_column",
        default: null,
        type: "str",
      },
      {
        name: "color_column",
        default: null,
        type: "str",
      },
      {
        name: "aggregation_type",
        default: "mean",
        type: "str",
      },
      {
        name: "color_scale",
        default: "YlGnBu",
        type: "str",
      },
    ],
  },
};
