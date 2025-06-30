from influxdb import InfluxDBClient
import json
import pandas as pd

client = InfluxDBClient(host="localhost", port=8086, database="precrisis")
# client.drop_measurement("safety_perception")

# cdf = pd.read_csv("Vienna_classification.csv")
# gdf = pd.read_csv("vienna_geoloc.csv").rename(columns={"uuid": "ID"}).reset_index(drop=True)

# df = cdf.merge(gdf, on="ID").drop(columns=["Unnamed: 0"])

# ls = json.loads(df.to_json(orient='records'))
# res = list(map(lambda x : {"measurement": "safety_perception", "fields": x, "tags": {"ID": x["ID"]}}, ls))

# print(res)

# client.write_points(res)

alerts = list(client.query('select * from video_anomaly_score where "score"::field > 0.6;').get_points())
locations = list(client.query('select lat,long,location from locations;').get_points())
print(client.query('select lat,long,location from locations;'))
ld = {}
for l in locations:
    ld[l["location"]] = l
alerts = list(map(lambda x : {"measurement": "alerts", "fields": x | {"lat": ld[x["location"]]["lat"], "long": ld[x["location"]]["long"]}, "tags": {"city": x["city"], "camera": x["camera"], "location": x["location"] }}, alerts))
client.write_points(alerts)
# client.drop_measurement("panic_module")
# client.drop_measurement("crowd_violence")
# client.drop_measurement("video_busca")
# client.drop_measurement("video_anomaly_score")



client.close()