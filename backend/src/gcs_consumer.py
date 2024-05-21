# Imports the Google Cloud client library
# Imports the Google Cloud client library
import json
import logging
from google.cloud.storage import Client, transfer_manager
import traceback
from colorama import Fore, Style
import pika


def success_str(msg=""):
    return f"{Fore.GREEN}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def error_str(msg=""):
    return f"{Fore.RED}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def log_str(msg=""):
    return f"{Fore.BLUE}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def warn_str(msg=""):
    return f"{Fore.YELLOW}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


# set to info and redirect logs to stdout
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()]
)
logging.info("finished imports")
parameters = pika.ConnectionParameters(host="localhost")
logging.info("finished connection")

# Establish
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# Declare a queue
queue_name = "gcs"
channel.queue_declare(queue=queue_name)


# Instantiates a client
storage_client = Client()

# The name for the new bucket
bucket_name = "defog-agents"
bucket = storage_client.bucket(bucket_name)


def store_files_to_gcs(ch, method, properties, body):
    logging.info(log_str("Storing files to GCS"))

    try:
        # try to parse with json. this should ideally be an array of file paths as a string
        paths = json.loads(body)

        # remove everything before "report-assets" from the path, but keep the "report-assets" part
        # if the path doesn't contain "report-assets", then the whole path is kept
        file_blob_pairs = [
            (path, bucket.blob(path[path.find("report-assets") :]))
            if path.find("report-assets") != -1
            else (path, bucket.blob(path))
            for path in paths
        ]

        logging.info(file_blob_pairs)

        # we can't use worker type "process" because spawing child process isn't allowed from daemons which is how i think the hypercorn server runs.
        transfer_manager.upload_many(file_blob_pairs, worker_type="thread")
        logging.info(success_str("Files stored to GCS"))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.info(error_str("Error storing files to GCS"))
        traceback.print_exc()


channel.basic_consume(
    queue=queue_name, on_message_callback=store_files_to_gcs, auto_ack=False
)

channel.start_consuming()
