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
        base = {
            "time": str(date_to_insert),
            "measurement": "panic_module",
            "tags": {"city": CITY, "camera": CAMERA, "location": LOCATION},
            "fields": {"score": float(data[i])},
        }

        influx_data.append(base)
        date_to_insert += timedelta(seconds=1)

# inser clips if any

workdir = os.path.dirname(os.path.abspath(FILENAME))

mp4_files = glob.glob(os.path.join(workdir, "*.mp4"))

for f in mp4_files:
    file_name = os.path.basename(f)
    base = {
        "time": str(date_to_insert),
        "measurement": "panic_module_clips",
        "tags": {"city": CITY, "camera": CAMERA, "location": LOCATION},
        "fields": {"clip_name": file_name},
    }

    influx_data.append(base)

    shutil.copy2(f, OUTPUTFOLDER)

with open("{}/cp.json".format(OUTPUTFOLDER), "w") as outfile:
    json.dump(influx_data, outfile)
