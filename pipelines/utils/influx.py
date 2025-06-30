from influxdb import InfluxDBClient
import json

client = InfluxDBClient(host="localhost", port=8086, database="precrisis")
client.drop_measurement("thumbnails_busca_full")

result = client.query('select * from thumbnails_busca;')

ls = list(result.get_points())
for p in ls:
    p["camera"] = p["camera"].replace("_", "").replace(".", "") + ".mp4"

res = list(map(lambda x : {"measurement": "thumbnails_busca_full", "fields": x, "tags": {"camera": x["camera"]}}, ls))
#print(len(res))
client.write_points(res)

client.close()