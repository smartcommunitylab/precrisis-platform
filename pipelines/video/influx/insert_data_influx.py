import json
import os
import sys

from influxdb import InfluxDBClient

client = InfluxDBClient(host="localhost", port=8086, database="precrisis")

directory = sys.argv[1]

for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith(".json"):
            file_path = os.path.join(root, file)
            with open(file_path, "r") as f:
                data = json.load(f)
                for d in data:
                    try:
                        client.write_points([d])
                    except Exception as e:
                        print(f"Error writing data to InfluxDB: {e}")
                        print(f"Data: {d}")
        # if file.endswith("_busca.mp4"):
        #     pass


client.close()
