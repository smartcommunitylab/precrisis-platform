# Process Data for Social Media Analysis

## Emotion Analysis

Copy the csv files to the `./content3/precrisis-text-analysis/` folder.

Run the `pipelines/socialmedia/emotions/Vienna_text_analysis.ipynb` Notebook, the results will be stored on `text_analysis_vienna.json`.

## Insert Data into InfluxDB

Install the `influxdb` library with the following command:

```shell
pip install influxdb
```

Run the following script, passing the JSON output data path as an argument:

```shell
python influx/insert_points.py text_analysis_vienna.json
```


## Points of Interest

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

## Insert Data into InfluxDB

Install the `influxdb` library with the following command:

```shell
pip install influxdb
```

Run the following script, passing the JSON output data path as an argument:

```shell
python influx/insert_points.py outputfile.json
```

