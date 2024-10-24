# Process Data for Social Media Analysis

## Emotion Analysis

Edit the notebook and add the following lines to the notebook:

```python
locations = ['Allianz_Stadion',
             'Donauinsel',
             'Ernst_Happel_Stadion',
             'Heldenplatz',
             'Rathausplatz',
             'Schottenring',
             'Waehring']
emotions = ["anger", "anticipation", "disgust", "fear", "joy", "sadness", "surprise", "trust"]

emotion_plot_data = []

for location in locations:
    dataframe = pd.read_csv(f"./content3/precrisis-text-analysis/{location}_dataset_EmotionsNorm_mean.tsv", sep="\t")
    for emotion in emotions:
        d = {"city": "Vienna","location": location, "emotion": emotion, "score": float(dataframe[emotion].values[0])}
        base = {
                "measurement": "emotions",
                "tags": d,
                "fields": d,
            }
        emotion_plot_data.append(base)

emotion_plot_data
    
```

```python
import base64

plots = []
for location in wordcloud_dict:
    for emotion in wordcloud_dict[location]:
        wc = wordcloud_dict[location][emotion]
        print("\n\n")
        print(f"{location.upper()} - {emotion.split('_')[-1]} emotions")
        plt.figure(figsize=(20, 20))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        plt.savefig("myimage.png", format='png')
        with open("myimage.png", "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            base = {
                "measurement": "wordclouds",
                "tags": {"city": "Vienna", "location": location},
                "fields": {"location": location, "image": encoded_string.decode("utf-8")},
            }
            plots.append(base)
print(plots)
```

```python
import json
all = emotion_plot_data + plots

with open("text_analysis_vienna.json", "w") as j:
    json.dump(all, j)
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

