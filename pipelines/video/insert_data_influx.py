from influxdb import InfluxDBClient
import json
import ast
import os
import cv2


client = InfluxDBClient(
                host="localhost", port=8086, database="precrisis"
            )

directory = "/home/vbezerra/Documents/to_be_deleted"

for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith(".json"):
            file_path = os.path.join(root, file)
            with open(file_path, "r") as f:
                data = json.load(f)
                for d in data:
                    client.write_points([d])
        if file.endswith("_busca.mp4"):
            pass


client.close()