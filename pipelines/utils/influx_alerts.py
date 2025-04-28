from influxdb import InfluxDBClient
import json
import pandas as pd

client = InfluxDBClient(host="localhost", port=8086, database="precrisis")
client.drop_measurement("alerts")

alerts = list(client.query('select * from video_anomaly_score where "score"::field > 0.6;').get_points())
locations = list(client.query('select lat,long,location from locations;').get_points())
print(client.query('select lat,long,location from locations;'))
ld = {}
for l in locations:
    ld[l["location"]] = l
alerts = list(map(lambda x : {"measurement": "alerts", "fields": x | {"lat": ld[x["location"]]["lat"], "long": ld[x["location"]]["long"]}, "tags": {"city": x["city"], "camera": x["camera"], "location": x["location"] }}, alerts))
client.write_points(alerts)


client.close()