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

    counter = 0

    for d in data:

        d["tags"]["city"] = CITY
        d["fields"]["city"] = CITY

        d["tags"]["camera"] = CAMERA
        d["fields"]["camera"] = CAMERA

        d["tags"]["location"] = LOCATION
        d["fields"]["location"] = LOCATION

        d["time"] = str(date_to_insert)
        d["fields"]["avg_speed"] = float(d["fields"]["avg_speed"])
        d["fields"]["avg_age"] = float(d["fields"]["avg_age"])
        d["fields"]["highest_speed"] = float(d["fields"]["highest_speed"])
        d["fields"]["min_speed"] = float(d["fields"]["min_speed"])

        counter += 1

        if counter > 5:
            counter = 0
            date_to_insert += timedelta(seconds=1)

        influx_data.append(d)

workdir = os.path.dirname(os.path.abspath(FILENAME))

mp4_files = glob.glob(os.path.join(workdir, "*.mp4"))

for f in mp4_files:
    file_name = os.path.basename(f)

    base = {
        "time": str(datetime.strptime(ORIGINAL_DATE, REGEX_TIME)),
        "measurement": "video_busca",
        "tags": {"city": CITY, "camera": CAMERA, "location": LOCATION},
        "fields": {
            "city": CITY,
            "camera": CAMERA,
            "location": LOCATION,
            "inspect": file_name,
        },
    }

    influx_data.append(base)

    shutil.copy2(f, OUTPUTFOLDER)

with open("{}/bc.json".format(OUTPUTFOLDER), "w") as outfile:
    json.dump(influx_data, outfile)
