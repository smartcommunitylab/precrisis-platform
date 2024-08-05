import glob
import json
import os
import shutil
import sys
from datetime import date, datetime, time, timedelta

FILENAME = sys.argv[1]
CITY = sys.argv[2]
CAMERA = sys.argv[3]
LOCATION = sys.argv[4]
ORIGINAL_DATE = sys.argv[5]
OUTPUTFOLDER = sys.argv[6]

REGEX_TIME = "%m/%d/%y %H:%M:%S"

with open(FILENAME, "r") as f:
    data = json.load(f)
    influx_data = []

    date_to_insert = datetime.strptime(ORIGINAL_DATE, REGEX_TIME)
    for d in data:
        base = {
            "time": str(date_to_insert),
            "measurement": "crowd_violence",
            "tags": {"city": CITY, "camera": CAMERA, "location": LOCATION},
            "fields": {
                "city": CITY,
                "camera": CAMERA,
                "location": LOCATION,
                "prob": d["prob"],
            },
        }

        date_to_insert += timedelta(seconds=1)

        influx_data.append(data)


with open("{}/cv.json".format(OUTPUTFOLDER), "w") as outfile:
    json.dump(influx_data, outfile)
