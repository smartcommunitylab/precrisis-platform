from influxdb import InfluxDBClient
import json

client = InfluxDBClient(host="localhost", port=8086, database="precrisis")
client.drop_measurement("object_tracker")
client.drop_measurement("video_busca")
client.drop_measurement("video_anomaly_score")
client.drop_measurement("crowd_violence")
client.drop_measurement("panic_module")
client.drop_measurement("panic_module_clips")
client.drop_measurement("alerts")

client.close()