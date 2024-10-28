# Social Media Analysis Tables

This document outlines the steps to analyze video files and integrate them into Grafana and InfluxDB.

# Run InfluxDB

```shell
docker run -p 8083:8083 -p 8086:8086 -v "$(pwd)":/var/lib/influxdb influxdb:1.8.10
```

# Social Media Analysis Cookbook

In this document we describe the steps to perform the analysis of social media files and insert into Grafana and InfluxDB.

## Places of Interest

### Dependencies:


```shell
pip install geopandas geopy networkx osmnx shapely 
```

### Create Points

Edit `points_of_interest.py` and insert the locations in the `LOCATIONS` variable, such as:

```python
{
    "Location_Name": (0, 0),
    "Donauinsel": (48.21069623, 16.43500653),
}   
```

To run, set the `city` name as the first variable and the `outputfile` path:

```shell
python points_of_interest.py Vienna outputs.json
```

### InfluxDB Data

The data object consists of:

```json
{
    "measurement": "points_of_interest",
    "tags": {
        "city": "City Name",
        "poi_type": "Type of Location e.g hospitals, police, fire_station",
        "location": "Location Name",
        "radius": "Radius integer in KM",
    },
    "fields": {
        "geojson": "GeoJson Mark of the Location ",
        "city": "City Name",
        "poi_type": "Type of Location e.g hospitals, police, fire_station",
        "location": "Location Name",
        "radius": "Radius integer in KM",
    },
}
```


## Emotion Analysis


### InfluxDB Data

The data object consists of:

```json
{
  "measurement": "emotions",
  "tags": {
    "city": "City Name",
    "location": "Location Name",
    "emotion": "Name of the emotion e.g. fear, anger, joy",
    "score": "Score value in Float",
  },
  "fields": {
    "city": "City Name",
    "location": "Location Name",
    "emotion": "Name of the emotion e.g. fear, anger, joy",
    "score": "Score value in Float"
  }
}
```

```json
{
  "measurement": "wordclouds",
  "tags": {
    "city": "City Name",
    "location": "Location Name"
  },
  "fields": {
    "location": "Location Name",
    "image": "Image of a Worldcloud stored in a string in base64"
  }
}

```