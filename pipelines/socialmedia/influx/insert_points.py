import json
import sys

from influxdb import InfluxDBClient

client = InfluxDBClient(host="localhost", port=8086, database="precrisis")

with open(sys.argv[1], "r") as input_file:
    data = json.load(input_file)
    for d in data:
        try:
            client.write_points([d])
        except Exception as e:
            print(e)

    client.close()
