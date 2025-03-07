"""
Utilities for Excel file cleaning.
"""

import re
import os
import asyncio
import concurrent.futures
import tempfile
from io import BytesIO

import pandas as pd
import openpyxl
from openai import AsyncOpenAI
from defog.llm.utils import LLM_COSTS_PER_TOKEN

from .name_utils import NameUtils
from utils_logging import LOGGER


class ExcelUtils:
    """Utilities for Excel file cleaning."""

    @staticmethod
    async def clean_excel_pd(excel_file: BytesIO) -> dict[str, pd.DataFrame]:
        """
        This function cleans all sheets in an Excel file with pandas by:
        - forward-filling merged cells
        - removing empty rows and columns
        - filling NaN values with empty strings

        Returns a dictionary of dataframes with sheet names as keys.
        """
        wb = openpyxl.load_workbook(excel_file)
        tables = {}

        async def process_sheet(sheet_name: str):
            sheet = wb[sheet_name]

            # Create a dictionary to store merged cell values
            merged_cells_map = {}

            # Identify merged cells and store only the top-left value
            for merged_range in sheet.merged_cells.ranges:
                min_col, min_row, max_col, max_row = merged_range.bounds
                top_left_value = sheet.cell(
                    row=min_row, column=min_col
                ).value  # Get top-left cell value

                # Store top-left value for all merged cells (but only modify in Pandas)
                for row in range(min_row, max_row + 1):
                    for col in range(min_col, max_col + 1):
                        merged_cells_map[(row, col)] = top_left_value

            # Convert worksheet data into Pandas DataFrame
            df = pd.DataFrame(sheet.values)

            # Use Pandas to forward-fill merged cell values
            for (row, col), value in merged_cells_map.items():
                if pd.isna(
                    df.iloc[row - 1, col - 1]
                ):  # Adjust index for Pandas (0-based)
                    df.iloc[row - 1, col - 1] = value
                    
            # Define common NULL/NA string representations
            null_values = [
                "NULL", "null", 
                "NA", "N/A", "n/a", "N.A.", "n.a.",
                "-", "--", "---",
                "#N/A", "#NA", "#NULL",
                "NaN", "nan",
                "None", "none",
                "", " ", "  "
            ]
            
            # Replace NULL string representations with NaN
            df = df.replace(null_values, pd.NA)
            
            # Trim trailing whitespace from string columns
            for col in df.columns:
                if df[col].dtype == 'object':  # String columns in pandas are 'object' type
                    df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

            # Remove rows that are empty
            df.dropna(inplace=True, how="all")

            # Drop columns where all values are NaN
            df = df.dropna(axis=1, how="all")

            # Fill NaN values with empty strings for better readability
            df = df.fillna("")

            # Clean sheet name
            table_name = NameUtils.clean_table_name(sheet_name, existing=tables.keys())

            LOGGER.info(
                f"Sheet {sheet_name} after dropping NaN rows/columns: {df.shape[0]} rows, {df.shape[1]} columns"
            )

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
                    for sheet_name in wb.sheetnames
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
            
        try:
            # Check for potential header/title rows at the top
            # Headers often have merged cells shown as the same value repeated
            head_rows = df.head(3)
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
            same_value_rows = df[df.apply(
                lambda row: len(set(row.dropna())) == 1 and len(row.dropna()) > 1, axis=1
            )]
            has_section_headers = not same_value_rows.empty
            
            # Check for aggregate statistics rows (containing "total", "sum", etc.)
            has_aggregate_rows = False
            for _, row in df.iterrows():
                row_str = " ".join([str(x).lower() for x in row])
                if any(agg in row_str for agg in ["total", "sum", "subtotal", "average", "mean"]):
                    has_aggregate_rows = True
                    break
            
            # Check if it's in wide format (many columns with similar naming patterns)
            # Wide format often has repeated column name patterns
            col_names = [str(col).lower() for col in df.columns]
            repeated_patterns = []
            for i in range(len(col_names)):
                for j in range(i+1, len(col_names)):
                    # Check if columns follow patterns like "X 2020", "X 2021" or "Q1 X", "Q2 X"
                    pattern = re.findall(r'[a-z]+', col_names[i])
                    if pattern and any(p in col_names[j] for p in pattern):
                        repeated_patterns.append((col_names[i], col_names[j]))
            has_wide_format = len(repeated_patterns) > len(df.columns) * 0.3
            
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
        LOGGER.info(f"Run cost in cents: {cost}")
        return df