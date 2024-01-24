# goes throgh the agent-assets/report-assets/datasets folder in the volume
# and deletes all files that are more than 15 minutes old
# this is to prevent the volume from filling up with old files


import os

from datetime import datetime, timedelta

files = os.listdir("/agents-assets/report-assets/datasets")
# print current time
print("Delete cron ran.\nCurrent Time =", datetime.now(), "\n")


for file in files:
    # if it ends in .feather
    # and was modified > 15 minutes old
    # delete it
    if file.endswith(".feather"):
        file_path = "/agents-assets/report-assets/datasets/" + file
        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        if datetime.now() - file_time > timedelta(minutes=15):
            print("deleting file: " + file_path)
            os.remove(file_path)
