from influxdb import InfluxDBClient
import json
import pandas as pd

from PIL import Image
import base64
from io import BytesIO

def create_thumbnail(location):
    """
    Reads a JPG image from a file, generates a thumbnail, and returns it as a base64 string.

    Args:
        location (str): The location name used to construct the image file path.

    Returns:
        str: Base64 string of the thumbnail image.
    """
    try:
        # Construct the file path (assuming images are stored in a specific directory)
        image_path = f"./data/thumbs/{location}.jpg"
        
        # Open the image
        with Image.open(image_path) as img:
            # Create a thumbnail (resize while maintaining aspect ratio)
            img.thumbnail((280, 140))  # Resize to 100x100 or smaller
            
            # Save the thumbnail to a BytesIO buffer
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)
            
            # Encode the thumbnail in base64
            thumbnail_base64 = base64.b64encode(buffer.read()).decode("utf-8")
            
            return thumbnail_base64
    except Exception as e:
        print(f"Error creating thumbnail for {location}: {e}")
        return None

client = InfluxDBClient(host="localhost", port=8086, database="precrisis")
client.drop_measurement("locations")

city = "Sofia"
df = pd.read_csv(f"./data/{city.lower()}-locations.csv")
ls = df.to_dict(orient="records")
res = []
for i in range(len(ls)):
    e = {}
    res.append(e)
    e["location"] = ls[i]["name"]
    e["city"] = city
    e["lat"] = float(ls[i]["latitude"])
    e["long"] = float(ls[i]["longitude"])
    e["thumb"] = create_thumbnail(ls[i]["name"])

locations = list(map(lambda x : {"measurement": "locations", "fields": x, "tags": {"city": x["city"], "location": x["location"] }}, res))
client.write_points(locations)
client.close()
