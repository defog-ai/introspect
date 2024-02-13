# Imports the Google Cloud client library

from google.cloud.storage import Client, transfer_manager
import traceback
from utils import log_str, success_str, error_str

# Instantiates a client
storage_client = Client()

# The name for the new bucket
bucket_name = "defog-agents"
bucket = storage_client.bucket(bucket_name)


async def store_files_to_gcs(paths):
    err = None
    print(log_str("Storing chart images to GCS"))
    try:
        # remove everything before "report-assets" from the path, but keep the "report-assets" part
        # if the path doesn't contain "report-assets", then the whole path is kept
        file_blob_pairs = [
            (path, bucket.blob(path[path.find("report-assets") :]))
            if path.find("report-assets") != -1
            else (path, bucket.blob(path))
            for path in paths
        ]
        print(file_blob_pairs)
        # we can't use worker type "process" because spawing child process isn't allowed from daemons which is how i think the hypercorn server runs.
        transfer_manager.upload_many(file_blob_pairs, worker_type="thread")

        print(success_str("Chart images stored to GCS"))
    except Exception as e:
        print(error_str("Error storing chart images to GCS"))
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err


async def file_exists_in_gcs(path):
    try:
        blob = bucket.blob(path)
        return blob.exists()
    except Exception as e:
        print(error_str(f"Error checking file {path} in GCS"))
        print(e)
        traceback.print_exc()
        return False


async def get_file_from_gcs(path):
    blob = bucket.blob(path)
    err = None
    try:
        print(log_str("Downloading file from GCS"))
        blob.download_to_filename(path)
        print(success_str("File downloaded from GCS"))
    except Exception as e:
        print(error_str(f"Error downloading file {path} from GCS"))
        print(e)
        traceback.print_exc()
        err = str(e)

    return err
