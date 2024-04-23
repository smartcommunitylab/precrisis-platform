# Video Analysis Cookbook

This document outlines the steps to analyze video files and integrate them into Grafana and InfluxDB.

## Table of Contents

1. [Object Detector and Tracker (BUSCA)](#busca)
2. [Anomaly Detector (LAVAD)](#anomaly)
3. [Crowd Panic Module](#cpanic)
4. [Crowd Violence Module](#cviolence)

<a name="busca"></a>
## Object Detector and Tracker (BUSCA) 

### Installation

Clone the repository:

```
git clone https://gitlab.fbk.eu/lvaquerootal/PRECRISIS_BUSCA
```

Edit the `precrisis_demo.py` file and include the following changes:

```python
tracker = ...

data_influx = []

...

outputs = tracker.track(frame)
try:
    # calculate objects
    total = len(outputs)

    if total != 0:
        avg_speed = sum([out["speed"] for out in outputs])/total
        high_speed = max([out["speed"] for out in outputs])
        min_speed = min([out["speed"] for out in outputs])
        high_age = max([out["age"] for out in outputs])
        min_age = min(out["age"] for out in outputs)
        avg_age = sum([out["age"] for out in outputs])/total
        objects_aspect = len([out["aspect_ratio"] for out in outputs if out["aspect_ratio"] > 1])
    else:
        avg_speed = 0
        high_speed = 0
        min_speed = 0
        high_age = 0
        min_age = 0
        avg_age = 0
        objects_aspect = 0

    base = {
        "measurement": "object_tracker",
        "tags": {
            "city": "",
            "camera": args.path.split("/")[-1],
            "location": "",
        },
        "fields": {
            "city": "",
            "camera": args.path.split("/")[-1],
            "location": "",
            "number_objects": total,
            "avg_speed": avg_speed,
            "highest_speed": high_speed,
            "min_speed": min_speed,
            "objects_aspect": objects_aspect,
            "avg_age": avg_age,
            "high_age": high_age,
            "min_age": min_age
        },
    }
    data_influx.append(base)
except Exception as e:
    print(e)

...

# Closes all the frames 
cv2.destroyAllWindows()

# save json
with open(save_path+".json", "w") as f:
    json.dump(data_influx, f)
```

The data object consists of:

```json
{
    "measurement": "object_tracker",
    "tags": {
        "city": "City Name",
        "camera": "Video Name",
        "location": "Name of the Location",
    },
    "fields": {
        "city": "City Name",
        "camera": "Video Name",
        "location": "Name of the Location",
        "number_objects": "Total number of Objects",
        "avg_speed": "Average Speed of the Objects",
        "highest_speed": "Highest Speed of the Objects",
        "min_speed": "Minimum Speed of the Objects",
        "objects_aspect": "Number of Objects with Aspect Ratio above 1",
        "avg_age": "Average Age of Objects (Number of Frames)",
        "high_age": "Highest Age of Objects (Number of Frames)",
        "min_age": "Minimum Age of Objects (Number of Frames)"
    }
}
```
### Running
---

For example, to process the file `palace.mp4`:

Inside the repository, run the following commands to build and run the container:

```
./build.sh
./run.sh
```

Then, inside the container, execute:

```
./precrisis_demo.py --path videos/palace.mp4 --device gpu
```

Navigate to the `BUSCA_OUTPUT` folder and convert the video to H256:

```
ffmpeg -i palace.mp4 -y palace_converted.mp4
```

Copy the converted video to the `videos` volume of Videoplayback. Insert the contents of the JSON file into Influx.

Add Thumbnail and Video into Database:


```python
THUMBNAIL_BUSCA = "Path to the Thumbnail file"
FILE_NAME = "palace.mp4"
LOCATION_NAME = "Location Name"
CITY = "Name of the City"

# insert busca thumb
with open(THUMBNAIL_BUSCA, "rb") as file:
    encoded_file = base64.b64encode(file.read())
    data = {
        "measurement": "thumbnails_busca",
        "tags": {"city": CITY, "camera": FILE_NAME, "location": LOCATION_NAME},
        "fields": {
            "city": CITY,
            "camera": FILE_NAME,
            "location": LOCATION_NAME,
            "image": encoded_file.decode("utf-8"),
        },
    }

    # insert point

# insert busca video
data = {
    "measurement": "video_busca",
    "tags": {"city": CITY, "camera": FILE_NAME, "location": LOCATION_NAME},
    "fields": {
        "city": CITY,
        "camera": FILE_NAME,
        "location": LOCATION_NAME,
        "inspect": "https://precrisis.smartcommunitylab.it/show/videos/{}".format(VIDEO_FILE
        ),
    },
}

# insert point
```

<a name="anomaly"></a>
## Anomaly Detector (LAVAD) 

Clone the repository:

```bash
git clone https://github.com/luca-zanella-dvl/lavad
```


<a name="cpanic"></a>
## Crowd Panic Module

Download the tar image `certh_cv_precrisis_cpd_image.tar` and use Docker to load the image:

```
docker load < certh_cv_precrisis_cpd_image.tar
```

Create the following folders : 
```
test_videos
Uploads
```

Add the videos to be processed into the `test_videos` folder and run the following command

```Docker
docker run -it --rm --gpus '"device=1,2"' -p 8080:8080 -v /raid/home/Uploads:/root/Uploads -v /raid/home/test_videos:/root/test_videos certh_cv_precrisis_cpd
```

The results are available in the `Upload` folder, if the model detects crowd panic clips will be created in a folder with the video name along with a JSON file with the detections.

Bellow a example of the JSON output:

```json
[
    {
        "video_path": "panic_clip_561.mp4",
        "duration": 2.0,
        "timestamp": 16.7,
        "abnormal_score": 1.0,
    },
    {
        "video_path": "panic_clip_1362.mp4",
        "duration": 1.8,
        "timestamp": 43.4,
        "abnormal_score": 0.85,
    },
    {
        "video_path": "panic_clip_1866.mp4",
        "duration": 2.1,
        "timestamp": 60.2,
        "abnormal_score": 0.83,
    },
    {
        "video_path": "panic_clip_2658.mp4",
        "duration": 1.9,
        "timestamp": 86.6,
        "abnormal_score": 0.9,
    },
    {
        "video_path": "panic_clip_3993.mp4",
        "duration": 1.8,
        "timestamp": 131.1,
        "abnormal_score": 0.93,
    },
    {
        "video_path": "panic_clip_6213.mp4",
        "duration": 2.0,
        "timestamp": 205.1,
        "abnormal_score": 0.8,
    },
    {
        "video_path": "panic_clip_7719.mp4",
        "duration": 1.9,
        "timestamp": 255.3,
        "abnormal_score": 0.77,
    }
]
```
To add to the database follow the following format:

```json
{
    "measurement": "panic_module",
    "tags": {
        "city": "City Name",
        "camera": "File Name",
        "location": "Location Name"
    },
    "fields": {
        "video_path": "Video name ex: panic_clip_7719.mp4",
        "duration": "Duration",
        "timestamp": "Timestamp",
        "abnormal_score": "Abnormal Score",
    },
}
```

Add the thumbnail:

```python
import base64

with open(THUMBNAIL_FILE, "rb") as file:
    encoded_file = base64.b64encode(file.read())
    data = {
        "measurement": "panic_module_thumb",
        "tags": {"city": CITY, "camera": FILE_NAME, "location": LOCATION_NAME},
        "fields": {
            "city": CITY,
            "camera": FILE_NAME,
            "location": LOCATION_NAME,
            "image": encoded_file.decode("utf-8"),
        },
    }

    # insert point
```

Convert the clips using the following command:

```
ffmpeg -i panic_clip_7719.mp4 -y panic_clip_7719_converted.mp4
```

Copy the converted video to the `videos` volume of Videoplayback.

<a name="cviolence"></a>
## Crowd Violence Module

Download the tar image `certh_ca_violence_v2.tar` and use Docker to load the image:

```
docker load < certh_ca_violence_v2.tar
```

Create the following folders : 
```
outputs
videos
```

Add the videos to be processed into the `test_videos` folder and run the following command

```Docker
docker run -it -v /raid/home/videos:/app/Input_videos -v /raid/home/outputs:/app/Output --gpus '"device=1,2"' --rm certh_ca_ma_demo:0.0.6
```

The results should be available in the `outputs` folder with a JSON file with the scores and a png graph ploting the score over time. To add the results in InfluxDB use the following table:


```json
{
    "measurement": "crowd_violence",
    "tags": {
        "city": "City Name",
        "camera": "Video File",
        "location": "Location Name"
    },
    "fields": {
        "city": "City Name",
        "camera": "Video File",
        "location": "Location Name",
        "prob": "Prob from JSON file",
    }
}
```

