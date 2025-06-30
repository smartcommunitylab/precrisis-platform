import glob
import json
import os
import shutil
import sys
from datetime import date, datetime, time, timedelta

from influxdb import InfluxDBClient
import json
import pandas as pd

client = InfluxDBClient(host="localhost", port=8086, database="precrisis")
client.drop_measurement("crowd_violence")

PATH = "/Users/raman/projects/SmartCommunity/precrisis/JSONs/"
CITY = "Vienna"
ORIGINAL_DATE = "07/02/24 16:23:06"
OUTPUTFOLDER = "/Users/raman/workspace/precrisis-platform/output"

REGEX_TIME = "%m/%d/%y %H:%M:%S"

locations = {
    "2": "Donauinsel",
    "3": "Waehring",
    "5": "Schottenring",
    "1": "Rathausplatz",
    "4": "Heldenplatz"
}

files = os.listdir(PATH)
influx_data = []
for FILENAME in files:
    LOCATION = locations[FILENAME[0]]
    CAMERA = FILENAME.replace("_", "").replace("-", "").replace(".json", "mkv.mp4")
    with open( os.path.join(PATH, FILENAME), "r") as f:
        data = json.load(f)
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
            date_to_insert += timedelta(milliseconds=640)
            influx_data.append(base)


# with open("{}/cv.json".format(OUTPUTFOLDER), "w") as outfile:
#     json.dump(influx_data, outfile)

client.write_points(influx_data)
res = list(client.query('select * from crowd_violence;').get_points())
print(res)
