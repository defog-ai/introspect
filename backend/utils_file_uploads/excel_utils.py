"""
Utilities for Excel file cleaning.
"""

import re
import os
import asyncio
import concurrent.futures
import tempfile
from io import BytesIO
import traceback

import pandas as pd
import openpyxl
from openai import AsyncOpenAI
from defog.llm.utils import LLM_COSTS_PER_TOKEN

from .name_utils import NameUtils
from .db_utils import DbUtils
from utils_logging import LOGGER


class ExcelUtils:
    """Utilities for Excel file cleaning."""

    @staticmethod
    async def clean_excel_pd(excel_file: BytesIO) -> dict[str, pd.DataFrame]:
        """
        This function cleans all sheets in an Excel file with pandas by:
        - handling complex Excel file structures with multi-level headers
        - preserving merged cells
        - handling hierarchical or grouped column names
        - removing only completely empty rows
        - filling NaN values with empty strings

        Returns a dictionary of dataframes with sheet names as keys.
        """
        tables = {}
        
        # Define common NULL/NA string representations to standardize handling
        null_values = [
            "NULL", "null", 
            "NA", "N/A", "n/a", "N.A.", "n.a.",
            "#N/A", "#NA", "#NULL",
            "NaN", "nan",
            "None", "none",
            "", " ", "  "
        ]
        
        # Get all sheet names to process
        excel_file.seek(0)  # Reset file position to beginning
        xlsx = pd.ExcelFile(excel_file)
        sheet_names = xlsx.sheet_names
        
        async def process_sheet(sheet_name: str):
            # Reset file position
            excel_file.seek(0)
            
            # First try to determine if we have a complex multi-level header structure
            # Load a small preview to check
            preview_df = pd.read_excel(
                excel_file,
                sheet_name=sheet_name,
                nrows=10  # Just read first 10 rows to analyze
            )
            
            # Check for evidence of multi-level header structure
            # 1. Look for rows that have the same value repeated across multiple columns
            has_title_rows = False
            potential_header_row = 0
            
            for i in range(min(5, len(preview_df))):  # Check first 5 rows at most
                row_values = preview_df.iloc[i].astype(str)
                # If >40% of cells have the same value, it might be a title/header row
                if len(row_values.unique()) < len(row_values) * 0.6:
                    has_title_rows = True
                    potential_header_row = i + 1  # Skip this row and consider next as header
            
            # Reset file position
            excel_file.seek(0)
            
            # If we detected title rows, try to handle them
            if has_title_rows:
                # Use the detected header row or rows
                # We'll try to use multiple rows as headers
                try:
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        header=[potential_header_row, potential_header_row+1] 
                        if potential_header_row < len(preview_df) - 1 
                        else potential_header_row
                    )
                    
                    # Check if we have tuple column names from multi-level headers
                    if isinstance(df.columns[0], tuple):
                        # Create better column names by joining levels
                        new_cols = []
                        for i, col in enumerate(df.columns):
                            # Filter out None/NaN/empty values
                            parts = [str(part).strip() for part in col 
                                     if part is not None and str(part).strip() != ""]
                            # Join with underscore
                            if parts:
                                new_cols.append("_".join(parts))
                            else:
                                # Use col_N instead of unnamed
                                new_cols.append(f"col_{i+1}")
                        
                        # Use centralized deduplication function
                        safe_cols = DbUtils.deduplicate_column_names(new_cols)
                        
                        # Log all column names to help debug
                        LOGGER.info(f"Original tuple columns: {df.columns}")
                        LOGGER.info(f"Created column names: {safe_cols}")
                        
                        df.columns = safe_cols
                except Exception as e:
                    # If multi-header approach fails, fall back to simpler method
                    LOGGER.warning(f"Multi-header detection failed: {e}. Using default.")
                    excel_file.seek(0)
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        na_values=null_values
                    )
            else:
                # Standard approach for simpler Excel files
                df = pd.read_excel(
                    excel_file,
                    sheet_name=sheet_name,
                    na_values=null_values
                )
                
                # Ensure column uniqueness even for simple headers
                if len(df.columns) != len(set(df.columns)):
                    # Use centralized deduplication function
                    safe_cols = DbUtils.deduplicate_column_names(df.columns)
                    LOGGER.info(f"Deduplicated columns: {safe_cols}")
                    df.columns = safe_cols
            
            # Remove rows that are entirely empty
            df.dropna(how='all', inplace=True)
            
            # Don't drop columns that might appear empty due to merged cells/formatting
            df.dropna(axis=1, how='all', inplace=True)
            
            # Trim trailing whitespace from string columns
            for col in df.columns:
                if df[col].dtype == 'object':  # String columns in pandas are 'object' type
                    df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
            
            # Fill NaN values with empty strings for better readability
            df = df.fillna("")
            
            # Clean sheet name
            table_name = NameUtils.clean_table_name(sheet_name, existing=tables.keys())
            
            LOGGER.info(
                f"Sheet {sheet_name} after cleaning: {df.shape[0]} rows, {df.shape[1]} columns"
            )
            LOGGER.info(f"Columns: {df.columns}")
            
            return table_name, df
        
        async def main():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                tasks = [
                    loop.run_in_executor(
                        executor,
                        lambda sheet_name=sheet_name: asyncio.run(
                            process_sheet(sheet_name)
                        ),
                    )
                    for sheet_name in sheet_names
                ]
                results = await asyncio.gather(*tasks)
                for table_name, df in results:
                    tables[table_name] = df
        
        await main()
        
        return tables

    @staticmethod
    async def is_table_dirty(table_name: str, df: pd.DataFrame) -> bool:
        """
        Checks if an Excel dataframe needs additional cleaning with OpenAI.
        Returns True if the dataframe appears to need cleaning.
        
        Criteria for "dirty" Excel/CSV files:
        1. Headers/titles at the top that aren't part of the data
        2. Footnotes or notes at the bottom
        3. Rows where all values are the same (potential section headers)
        4. Rows with aggregate statistics (like "Total", "Sum", etc.)
        5. Wide format tables that should be transformed to long format
        """
        if df.empty or len(df) < 3:
            return False
        
        # this is a threshold for header checks
        HEADERS_CHECK_THRESHOLD = 20
        try:
            # Check for potential header/title rows at the top
            # Headers often have merged cells shown as the same value repeated
            # if there are more than 10 rows, check the first 3 rows
            # else just check the first row
            # not the most logical of ifs but prevents unnecessary checks in really small csvs (restaurants is a good example)
            head_rows = df.head(3 if len(df) > HEADERS_CHECK_THRESHOLD else 1)
            has_repeated_headers = head_rows.apply(
                lambda row: len(set(row.astype(str))) < len(row) * 0.5, axis=1
            ).any()
            
            # Check for potential footer rows
            tail_rows = df.tail(3)
            # Check for repeated values in footer rows (similar to headers)
            has_repeated_footers = tail_rows.apply(
                lambda row: len(set(row.astype(str))) < len(row) * 0.5, axis=1
            ).any()
            has_footer_notes = has_repeated_footers
            for _, row in tail_rows.iterrows():
                # Look for rows with few distinct values or text indicators
                text_values = [str(x).lower() for x in row if isinstance(x, str)]
                if text_values and any(note in " ".join(text_values) 
                                      for note in ["note", "source", "*", "total", "sum"]):
                    has_footer_notes = True
                    break
            
            # Check for rows where all non-null values are the same (section headers)
            if len(df) > HEADERS_CHECK_THRESHOLD:
                same_value_rows = df[df.apply(
                    lambda row: len(set(row.dropna())) == 1 and len(row.dropna()) > 1, axis=1
                )]
                has_section_headers = not same_value_rows.empty
            else:
                has_section_headers = False
            
            # Check for aggregate statistics rows (containing "total", "sum", etc.)
            has_aggregate_rows = False
            if len(df) > HEADERS_CHECK_THRESHOLD:
                # Pre-compute columns to check
                # we only check the first and last three columns
                num_cols = len(df.columns)
                # Handle cases with fewer than 6 columns
                if num_cols <= 6:
                    # If fewer than 6 columns, just check all columns
                    columns_to_check = list(range(num_cols))
                else:
                    # Otherwise check first and last three
                    columns_to_check = [0, 1, 2, num_cols - 3, num_cols - 2, num_cols - 1]
                
                agg_words = ["total", "sum", "subtotal", "average", "mean"]
                
                # Filter to only the columns we need to check
                subset_df = df.iloc[:, columns_to_check]
                
                # Convert all values to lowercase strings
                subset_df = subset_df.astype(str).apply(lambda x: x.str.lower())
                
                # Check if any cell exactly matches one of the aggregate words
                # This creates a DataFrame of boolean values where True means a match
                matches = subset_df.isin(agg_words)
                
                # Check if any row has at least one match
                has_aggregate_rows = matches.any(axis=1).any()
            
            # Check if it's in wide format (many columns with similar naming patterns)
            # Wide format often has repeated column name patterns
            col_names = df.columns
            def detect_repeating_pattern(str1, str2):
                # Convert to lowercase for comparison
                str1, str2 = str1.lower(), str2.lower()
                
                # To avoid false positives like 'average' and 'regionalaveragerecord',
                # require a common prefix at the start that's significant
                
                # Find common prefix
                common_prefix_len = 0
                common_prefix = ""
                for a, b in zip(str1, str2):
                    if a == b:
                        common_prefix += a
                        common_prefix_len += 1
                    else:
                        break
                

                if common_prefix_len == 0:
                    return False, None

                
                # Now check if only the ending parts differ
                suffix1 = str1[common_prefix_len:]
                suffix2 = str2[common_prefix_len:]
                
                # print(str1, str2, common_prefix, suffix1, suffix2, common_prefix_len)
                # Full column names should be similar (we want 'sales2020', 'sales2021', not 'sales', 'salesreport')
                if abs(len(str1) - len(str2)) > 3:
                    return False, common_prefix
                
                # If both suffixes are numeric, they could be sequential (like years)
                # just return true without putting any condition on the suffixes
                if suffix1.isdigit() and suffix2.isdigit():
                    return True, common_prefix
                
                # For non-numeric suffixes, only allow small variations at the end
                # Ensure the variation is small relative to the overall string length
                return len(suffix1) <= 3 and len(suffix2) <= 3, common_prefix

            prefixes = {}

            for i in range(len(col_names)):
                for j in range(i+1, len(col_names)):
                    # Enhanced check for repeating patterns with small variations
                    # like "1991", "1992", "1993" or "Jan-22", "Feb-22", "Mar-22"
                    is_repeating, common_prefix = detect_repeating_pattern(str(col_names[i]), str(col_names[j]))
                    
                    if is_repeating:
                        if common_prefix not in prefixes:
                            prefixes[common_prefix] = set()
                        prefixes[common_prefix].add(col_names[i])
                        prefixes[common_prefix].add(col_names[j])


            # if prefix has keys, and all keys have more than 2 columns
            # then wide format is True
            has_wide_format = False
            for key in prefixes.keys():
                if len(prefixes[key]) > 2:
                    LOGGER.info(f"Prefixes found that qualify this db for wide format: {prefixes}")
                    has_wide_format = True
                    break
            
            # Return True if any of the criteria are met
            is_dirty = has_repeated_headers or has_footer_notes or has_section_headers or has_aggregate_rows or has_wide_format
            
            if is_dirty:
                LOGGER.info(f"Table {table_name} requires further cleaning with OpenAI. Reasons: " +
                           f"repeated headers: {has_repeated_headers}, " +
                           f"footer notes: {has_footer_notes}, " +
                           f"section headers: {has_section_headers}, " +
                           f"aggregate rows: {has_aggregate_rows}, " +
                           f"wide format: {has_wide_format}")
            else:
                LOGGER.info(f"Table {table_name} is clean, skipping OpenAI cleaning")
            
            return is_dirty
            
        except Exception as e:
            traceback.print_exc()
            LOGGER.error(f"Error checking if table is dirty. Defaulting to further cleaning by OpenAI: {e}")
            # If we encounter an error during checking, default to further cleaning
            return True
    
    @staticmethod
    async def clean_excel_openai(table_name: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Further cleans a dataframe using OpenAI's Code Interpreter. Dynamically generates and executes code to remove columns and rows that do not contribute to the data (e.g. headers and footnotes). Also if necessary, changes the dataframe from wide to long format that's suitable for PostgreSQL.
        """
        # Check if the dataframe actually needs cleaning
        needs_cleaning = await ExcelUtils.is_table_dirty(table_name, df)
        if not needs_cleaning:
            return df
        
        # Create a temporary file for upload to OpenaAI. Will be automatically deleted after uploading
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            df.to_csv(temp_file.name, index=False)
            file_path = temp_file.name
        
        client = AsyncOpenAI()

        try:
            csv_file = await client.files.create(
                file=open(file_path, "rb"), purpose="assistants"
            )
            LOGGER.info(
                f"Uploaded {table_name}.csv file to OpenAI for cleaning: {csv_file.id} "
            )
        except Exception as e:
            LOGGER.error(f"Failed to upload {table_name}.csv file to OpenAI: {e}")
            return df
        finally:
            # Clean up the temporary file
            if os.path.exists(file_path):
                os.remove(file_path)

        # Set up instructions and prompt
        instructions = "You are an expert in cleaning and transforming CSV files. Write and run code to execute transformations on CSV files."
        prompt = f"""Generate and execute a python script to clean and transform the provided CSV file that's been parsed from an Excel file.

    The script should perform the following tasks:
    0. Load the csv file as a dataframe
    1. Remove column indexes.
    2. Remove rows with titles or other plain text cells (e.g footnotes) that do not constitute the data. 
        - Inspect head and tail of dataframe.
        - Also inspect rows where all non-null values are the same with `df[df.apply(lambda row: len(set(row.dropna())) == 1, axis=1)]` to see if they are relevant data.
    3. Remove rows with aggregate statistics (i.e. Inspect rows with the word "total"," case-insensitively.)
    4. If table is in a wide format, change it to a long format so that it's suitable for a PostgreSQL database. Ensure no data is lost and that all columns are accounted for in the transformation. 
    5. Define meaningful column names for new columns.
    6. Generate a new CSV file with the cleaned and transformed data.

    Work with all the information you have. DO NOT ask further questions. Continue until the task is complete.
    """

        # Set up assistant, thread, message
        model = "gpt-4o"  # o3-mini currently doesn't support code interpreter
        assistant = await client.beta.assistants.create(
            instructions=instructions,
            model=model,
            tools=[{"type": "code_interpreter"}],
            tool_resources={"code_interpreter": {"file_ids": [csv_file.id]}},
        )
        thread = await client.beta.threads.create()

        message = await client.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=prompt
        )

        # Run the code
        try:
            LOGGER.info(f"Executing cleaning run on {table_name}")
            run = await client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant.id,
                instructions=instructions,
            )
        except Exception as e:
            LOGGER.error(f"Failed to create and poll cleaning run: {e}")
            return df

        # Keep checking status of run
        if run.status == "completed":
            LOGGER.info(f"Cleaning run on {table_name} completed")
            messages = await client.beta.threads.messages.list(thread_id=thread.id)
        else:
            LOGGER.error(
                f"Cleaning run on {table_name} did not complete successfully. Run status: {run.status}"
            )
            return df

        # Extract file to download
        file_to_download = None
        for m in messages.data:
            for content_block in m.content:
                if hasattr(content_block, "text") and hasattr(
                    content_block.text, "annotations"
                ):
                    for annotation in content_block.text.annotations:
                        if hasattr(annotation, "file_path") and hasattr(
                            annotation.file_path, "file_id"
                        ):
                            file_to_download = annotation.file_path.file_id
                            break

        # Download the file and convert to dataframe
        if file_to_download is not None:
            try:
                file_data = await client.files.content(file_to_download)
            except Exception as e:
                LOGGER.error(f"Failed to download {file_to_download}: {e}")
                return df

            try:
                file_data_bytes = file_data.read()
                df = pd.read_csv(BytesIO(file_data_bytes))
                LOGGER.info(f"Downloaded {file_to_download}")
            except Exception as e:
                LOGGER.error(f"Failed to read {file_to_download} as CSV: {e}")
                return df

            # Delete file in client
            await client.files.delete(file_to_download)
            LOGGER.info(f"Deleted {file_to_download} in client")
        else:
            LOGGER.info(f"No file to download.")

        # Calculate run cost
        LOGGER.info(f"Run usage: {run.usage}")
        output_tokens = run.usage.completion_tokens
        cached_input_tokens = run.usage.prompt_token_details.get("cached_tokens", 0)
        input_tokens = run.usage.prompt_tokens - cached_input_tokens

        cost = input_tokens / 1000 * LLM_COSTS_PER_TOKEN[model]["input_cost_per1k"]
        cost += output_tokens / 1000 * LLM_COSTS_PER_TOKEN[model]["output_cost_per1k"]
        cost += (
            cached_input_tokens
            / 1000
            * LLM_COSTS_PER_TOKEN[model]["cached_input_cost_per1k"]
        )
        cost *= 100
        cost += 3 # cost of code interpreter session
        LOGGER.info(f"Run cost in cents: {cost}")
        return df