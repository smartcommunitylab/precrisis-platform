from influxdb import InfluxDBClient
import json
import pandas as pd

classification_file = "Vienna_classification.csv"
geoloc_file = "vienna_geoloc.csv"

client = InfluxDBClient(host="localhost", port=8086, database="precrisis")
client.drop_measurement("safety_perception")

cdf = pd.read_csv(classification_file)
gdf = pd.read_csv(geoloc_file).rename(columns={"uuid": "ID"}).reset_index(drop=True)
df = cdf.merge(gdf, on="ID").drop(columns=["Unnamed: 0"])
ls = json.loads(df.to_json(orient='records'))
res = list(map(lambda x : {"measurement": "safety_perception", "fields": x, "tags": {"ID": x["ID"]}}, ls))
# print(res)

client.write_points(res)
client.close()