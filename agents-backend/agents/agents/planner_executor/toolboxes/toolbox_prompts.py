# - tool_name: simple_stats
#   description: Gets simple statistics from a pandas df using numpy and pandas.
#   inputs: [snippets of python code for each calculation]
#   outputs: [pandas dfs in the same order as the above snippets]


toolbox_prompts = {
    "data-fetching": """
- tool_name: data_fetcher_and_aggregator
  description: Converting a natural language question into a SQL query, that then runs on an external database. Fetches, filters, aggregates, and performs arithmetic computations on data. Remember that this tool does not have access to the data returned by the previous steps. It only has access to the data in the database.
  inputs: [natural language description of the data required to answer this question (or get the required information for subsequent steps) as a string]
  outputs: pandas df""",

    "stats": """- tool_name: dataset_metadata_describer
  description: Describes the columns available inside a dataset
  inputs: [None]
  outputs: pandas df

- tool_name: line_plot
  description: This function generates a line plot using python's seaborn library. It should be used when the user wants to see how a variable changes over time, and should be used immediately after the data_fetcher tool.
  inputs: [pandas df, xaxis column, yaxis column, hue column (optional)],
  outputs: pandas df
  
-tool_name: t_test
  description: This function gets two groups and runs a t-test to check if there is a significant difference between their means. There are two ways to run the test: paired and unpaired. Paired test has one group column, unpaired has one group column.
  inputs: [pandas df, group column, score column, name column, type of t test as a string (paired or unpaired)]
  outputs: pandas df

-tool_name: wilcoxon_test
    description: This function gets two groups and runs a wilcoxon test to check if there is a significant difference between their means.
    inputs: [pandas df, group column, score column, name column]
    outputs: pandas df

-tool_name: anova_test
    description: This function gets more than two groups and runs an anova test to check if there is a significant difference between their means.
    inputs: [pandas df, group column, score column]
    outputs: pandas df
""",
    "plots": """-tool_name: boxplot
    description: Generates a boxplot using python's seaborn library. Also accepts a faceting column. This usually required the full dataset and not summary statistics. Use the facet feature only when specifically asked for it.
    inputs: [pandas df, [boxplot_x column, boxplot_y column], facet = True/False, facet column]
    outputs: pandas df

-tool_name: heatmap
    description: Generates a heatmap using python's seaborn library. This accepts the full dataset as the first parameter, and not summary statistics or aggregates.
    inputs: [pandas df, heatmap_x_column, heatmap_y_column, heatmap_value_column, aggregation_type as a string (can be mean, median, max, min or sum), color_scale (only if specified by the user. defaults to YlGnBu)]
    outputs: pandas df
""",
    # --- --- --- #
    "cancer-survival": """
- tool_name: kaplan_meier_curve
    description: Generates a kaplan meier survival function. You have to run data_fetcher before this.
    inputs: [full patient data, survival time column name, status/event column name, [array of stratification variables if any otherwise None]]
    outputs: [multiple pandas dfs for each stratification variable. single df if stratification variables is None]
    
- tool_name: hazard_ratio
    description: Creates a hazard ratio (based on the Cox Index), given some inputs.
    inputs: [survival time column name, status/event column name]""",
}
