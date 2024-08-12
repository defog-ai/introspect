# This script just checks for a few things like file directory structure
# and creates them if they don't exist
import os

def setup_dir(app_root_path: str):
    oracle_path = os.path.join(app_root_path, "oracle")
    if not os.path.exists(oracle_path):
        os.makedirs(oracle_path)
        print("Created oracle directory.")
    oracle_reports_path = os.path.join(oracle_path, "reports")
    if not os.path.exists(oracle_reports_path):
        os.makedirs(oracle_reports_path)
        print("Created reports directory.")