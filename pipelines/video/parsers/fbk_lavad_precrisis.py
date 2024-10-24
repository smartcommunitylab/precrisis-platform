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
    for i in data:
        score = 0
        try:
            score = sum(data[str(i)].values()) / len(data[str(i)])
        except Exception as e:
            print(e)
        base = {
            "time": str(date_to_insert),
            "measurement": "video_anomaly_score",
            "tags": {"city": CITY, "camera": CAMERA, "location": LOCATION},
            "fields": {
                "city": CITY,
                "camera": CAMERA,
                "location": LOCATION,
                "score": score,
                "frame": i,
                "inspect": CAMERA + "_a.mp4",
            },
        }
        influx_data.append(base)
        date_to_insert += timedelta(seconds=1)

with open("{}/lavad.json".format(OUTPUTFOLDER), "w") as outfile:
    json.dump(influx_data, outfile)
