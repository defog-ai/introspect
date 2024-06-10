# - tool_name: simple_stats
#   description: Gets simple statistics from a pandas df using numpy and pandas.
#   inputs: [snippets of python code for each calculation]
#   outputs: [pandas dfs in the same order as the above snippets]


toolbox_prompts = {
    "data-fetching": """
- tool_name: data_fetcher_and_aggregator
  description: Converting a natural language question into a SQL query, that then runs on an external database. Fetches, filters, aggregates, and performs arithmetic computations on data. Remember that this tool does not have access to the data returned by the previous steps. It only has access to the data in the database.
  inputs: [natural language description of the data required to answer this question (or get the required information for subsequent steps) as a string]
  outputs: pandas df
  
- tool_name: global_dict_data_fetcher_and_aggregator
  description: Converting a natural language question into a SQL query, that then runs on a database that is stored in global_dict. Fetches, filters, aggregates, and performs arithmetic computations on data. This tool has access to all of global_dict. This will only run on the data that is stored in global_dict. For external databases, use the data_fetcher_and_aggregator tool.
  inputs: [natural language description of the data required as a string, "global_dict.<input_df_name>"]
  outputs: pandas df""",
    "stats": """- tool_name: line_plot
  description: This function generates a line plot using python's seaborn library. It should be used when the user wants to see how a variable changes over time, and should be used immediately after the data_fetcher tool.
  inputs: ["global_dict.<input_df_name>", xaxis column (exactly a single column - often a datetime or string), yaxis column (exactly a single column - always a numerical value), hue column or None, facet column or None, estimator ("mean" if data must be aggregated, "None" if it is not aggregated), individual_id_column or None - refers to the column that contains individual data points, often some kind of id), plot_average_line or None - True if the user wants to plot an average or median line, average_line_type or None - the kind of value for the average line to have. Can be mean, median, max, min, or mode]
  outputs: pandas df
  
-tool_name: t_test
  description: This function gets two groups and runs a t-test to check if there is a significant difference between their means. There are two ways to run the test: paired and unpaired. Paired test has one group column, unpaired has one group column.
  inputs: ["global_dict.<input_df_name>", group column, score column, name column or None, type of t test as a string (paired or unpaired)]
  outputs: pandas df

-tool_name: wilcoxon_test
  description: This function gets two groups and runs a wilcoxon test to check if there is a significant difference between their means.
  inputs: ["global_dict.<input_df_name>", group column, score column, name column]
  outputs: pandas df

-tool_name: anova_test
  description: This function gets more than two groups and runs an anova test to check if there is a significant difference between their means.
  inputs: ["global_dict.<input_df_name>", group column, score column]
  outputs: pandas df

- tool_name: fold_change
  description: This function calculates the fold change over time for different groups. Fold change is the ratio of the final value to the initial value.
  inputs: ["global_dict.<input_df_name>", value column (the numerical value), individual id column (the column that represents individual ids to calculate fold change for), time column (the column that represents the time point), group column or None (the column that represents the groups that individuals belong to, like cohort or study)]
  outputs: pandas
""",
    "plots": """-tool_name: boxplot
    description: Generates a boxplot using python's seaborn library. Also accepts a faceting column. This usually required the full dataset and not summary statistics. Use the facet feature only when specifically asked for it.
    inputs: ["global_dict.<input_df_name>", [boxplot_x column, boxplot_y column], facet = True/False, facet column]
    outputs: pandas df

-tool_name: heatmap
    description: Generates a heatmap using python's seaborn library. This accepts the full dataset as the first parameter, and not summary statistics or aggregates.
    inputs: ["global_dict.<input_df_name>", heatmap_x_column, heatmap_y_column, heatmap_value_column, aggregation_type as a string (can be mean, median, max, min or sum), color_scale (only if specified by the user. defaults to YlGnBu)]
    outputs: pandas df
""",
    # --- --- --- #
    "cancer-survival": """
- tool_name: kaplan_meier_curve
    description: Generates a kaplan meier survival function. You have to run data_fetcher before this.
    inputs: ["global_dict.<full_patient_data_df>", survival time column name, status/event column name, [array of stratification variables if any otherwise None]]
    outputs: [as many pandas dfs as there are stratification variables. Make sure the outputs length matches the number of stratification variables. only one pandas df is output if stratification variables is None]
    
- tool_name: hazard_ratio
    description: Creates a hazard ratio (based on the Cox Index), given some inputs.
    inputs: ["global_dict.<full_patient_data_df>", survival time column name, status/event column name]
    outputs: pandas df""",
}
