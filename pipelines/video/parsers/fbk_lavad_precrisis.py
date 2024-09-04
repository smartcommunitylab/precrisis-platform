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
    n_frames = len(data.keys())
    date_to_insert = datetime.strptime(ORIGINAL_DATE, REGEX_TIME)
    for i in range(n_frames):
        base = {
            "time": str(date_to_insert),
            "measurement": "video_anomaly_score",
            "tags": {"city": CITY, "camera": CAMERA, "location": LOCATION},
            "fields": {
                "city": CITY,
                "camera": CAMERA,
                "location": LOCATION,
                "score": data[str(i)],
                "frame": i,
                "inspect": CAMERA,
            },
        }
        influx_data.append(base)

with open("{}/lavad.json".format(OUTPUTFOLDER), "w") as outfile:
    json.dump(influx_data, outfile)