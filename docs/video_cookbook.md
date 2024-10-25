# Video Analysis Tables

This document outlines the steps to analyze video files and integrate them into Grafana and InfluxDB.

# Run InfluxDB

```shell
docker run -p 8083:8083 -p 8086:8086 -v "$(pwd)":/var/lib/influxdb influxdb:1.8.10
```

## Table of Contents

1. [Object Detector and Tracker (BUSCA)](#busca)
2. [Anomaly Detector (LAVAD)](#anomaly)
3. [Crowd Panic Module](#cpanic)
4. [Crowd Violence Module](#cviolence)

<a name="busca"></a>
## Object Detector and Tracker (BUSCA) 

### Installation

Clone the repository:

```shell
git clone https://gitlab.fbk.eu/lvaquerootal/PRECRISIS_BUSCA.git
```

Download [model_busca.pth](https://drive.google.com/file/d/1jRYMVOc5wid9paCgJdEd3RhSxBC32O2h/view?usp=sharing) and store it in `models/BUSCA/motsynth/`.
Download [model_feats.pth](https://drive.google.com/file/d/1ZNU0yNkhMTlLRSOC0PR82SwK1ic9OJ8Y/view?usp=sharing) and store it in `models/feature_extractor/market1501/`.
Download [bytetrack_x_mot17.pth.tar](https://drive.google.com/file/d/1P4mY0Yyd3PPTybgZkjMYhFri88nTmJX5/view?usp=sharing) and store it in `pretrained/`.

Edit the `precrisis_demo.py` file and replace its content with the content from the `pipelines/video/busca/precrisis_demo.py` file in this repository.

Build the Docker image:

```shell
docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) -f Dockerfile -t precrisis_busca-vbezerra-dsl-7 .
```

To execute, use the following command:

```shell
docker run --gpus "$GPU_DEVICE" \
 -it --rm -v "$(pwd)":/workspace/BUSCA \
 precrisis_busca-vbezerra-dsl-7 \
 python precrisis_demo.py --path videos/videofile.mp4 --device gpu
```

### InfluxDB Data

The data object consists of:

```json
{
    "measurement": "video_busca",
    "tags": {
        "city": "City Name",
        "camera": "Video File Name",
        "location": "Name of the Location"
    },
    "fields": {
        "city": "City Name",
        "camera": "Video File Name",
        "location": "Name of the Location",
        "inspect": "Video File path e.g. cam01001mp4.mp4_busca.mp4"
    }

}
```

```json
{
    "measurement": "object_tracker",
    "tags": {
        "city": "City Name",
        "camera": "Video File Name",
        "location": "Name of the Location",
    },
    "fields": {
        "city": "City Name",
        "camera": "Video File Name",
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

<a name="anomaly"></a>
## Anomaly Detector (LAVAD) 

Clone the repository:

```shell
git clone https://github.com/lucazanella/lavad.git
```

Copy the `lavad/run_eval.sh` file from this repository and place it in the `scripts` folder inside the `lavad` directory.

Edit the `requirements.txt` file and change the `numpy` version:

* From `numpy>=1.19` to `numpy==1.26.4`

Download `llama-2-13b-chat` from the official repository by following the [download instructions](https://github.com/meta-llama/llama#download) and place the model and the tokenizer in `libs/llama`.

Build the Docker image:

```shell
./scripts/docker_build.sh
```

To execute, use the following command:

```shell
docker run --shm-size 64gb --gpus "$GPU_DEVICE" --rm -it -u `id -u $USER` -v "$(pwd)":/usr/src/app -v "$(pwd)"/lavad_video:/usr/src/datasets lavad ./scripts/run_eval.sh
```

*Please note that LAVAD requires two GPUs with 32GB of VRAM each to run.*

### InfluxDB Data

The data object consists of:

```json
{
    "measurement": "video_anomaly_score",
    "tags": {
        "city": "City Name",
        "camera": "Video File Name",
        "location": "Name of the Location",
    },
    "fields": {
        "city": "City Name",
        "camera": "Video File Name",
        "location": "Name of the Location",,
        "score": "Float Score between 0 - 1",
        "frame": "Frame Number",
        "inspect": "LAVAD video output file e.g. cam01001mp4.mp4_a.mp4"
    }
}
```

<a name="cpanic"></a>
## Crowd Panic Module

CERTH has provided Docker images to be imported using Docker:

* Run: `docker load < certh_cv_precrisis_cpd_v2.tar`

To execute, use the following commands:

```shell
docker run -it --rm --gpus "$GPU_DEVICE" \
    -p 8080:8080 \
    -v "$workdir"/Uploads:/usr/src/app/Uploads \
    -v "$workdir"/Uploads/video_file.mp4:/usr/src/app/Uploads/video_file.mp4 \
    certh_cv_precrisis_cpd --video_path /usr/src/app/Uploads/video_file.mp4
```

### InfluxDB Data

The data object consists of:

```json
{
    "measurement": "panic_module",
    "tags": {
        "city": "City Name",
        "camera": "Video File Name",
        "location": "Name of the Location",
    },
    "fields": {
        "score": "Score Value"
    }
}
```

```json
{
    "measurement": "panic_module_clips",
    "tags": {
        "city": "City Name",
        "camera": "Video File Name",
        "location": "Name of the Location",
    },
    "fields": {
        "clip_name": "Video File output e.g. cam03001mp4.mp4_clip_1.mp4"
    }
}
```

<a name="cviolence"></a>
## Crowd Violence Module

CERTH has provided Docker images to be imported using Docker:

* Run: `docker load < certh_ca_violence_v2.tar`

To execute, use the following commands:

```shell
docker run -it -v "$workdir"/videos:/app/Input_videos -v "$workdir"/outputs:/app/Output --gpus "$GPU_DEVICE" --rm certh_ca_ma_demo:0.0.6
```

### InfluxDB Data

The data object consists of:

```json
{
    "measurement": "crowd_violence",
    "tags": {
        "city": "City Name",
        "camera": "Video File Name",
        "location": "Name of the Location",
    },
    "fields": {
        "city": "City Name",
        "camera": "Video File Name",
        "location": "Name of the Location",
        "prob": "Score Value"
    }
}
```