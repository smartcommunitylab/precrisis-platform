# Process Data for Video Analysis

## Installation

### DGX1 FBK

If running on the DGX1, navigate to `dvl/projects/vbezerra/precrisis_pipeline/` and run the `build.sh` script.

### From Scratch

##### Video Anonymization

Clone the repository:

```shell
git clone https://github.com/luca-zanella-dvl/marvel-videoanony.git
```

First, create the `weights` folder in the root project directory.
   
```bash
mkdir weights
```

Then, download the pretrained models from [Google Drive](https://drive.google.com/drive/folders/1YfZ-WSh5W1fCnje4fMgaY9EsXH2xMNnP?usp=sharing) and
save them under the `weights` folder.

Build the Docker image:

```shell
docker build -t anonymisation-vbezerra-dsl-1:latest .
```

To execute, use the following command:

```shell
docker run -it -v "$(pwd)":/app -u `id -u $USER` --gpus "$GPU_DEVICE" anonymisation-vbezerra-dsl-1:latest python src/anonymize.py --source videos/video_file.mp4

```

##### Crowd Panic and Crowd Violence

CERTH has provided Docker images to be imported using Docker:

* Download the images `certh_ca_violence_v2.tar` and `certh_cv_precrisis_cpd_v2.tar`.
* Run: `docker load < certh_ca_violence_v2.tar`
* Run: `docker load < certh_cv_precrisis_cpd_v2.tar`

To execute, use the following commands:

```shell
docker run -it -v "$workdir"/videos:/app/Input_videos -v "$workdir"/outputs:/app/Output --gpus "$GPU_DEVICE" --rm certh_ca_ma_demo:0.0.6
```

```shell
docker run -it --rm --gpus "$GPU_DEVICE" \
    -p 8080:8080 \
    -v "$workdir"/Uploads:/usr/src/app/Uploads \
    -v "$workdir"/Uploads/video_file.mp4:/usr/src/app/Uploads/video_file.mp4 \
    certh_cv_precrisis_cpd --video_path /usr/src/app/Uploads/video_file.mp4
```

##### BUSCA (Object Detector)

Clone the repository:

```shell
git clone https://gitlab.fbk.eu/lvaquerootal/PRECRISIS_BUSCA.git
```

Download the `models` and `pretrained` from the Google Drive (https://drive.google.com/drive/folders/16CKlk6LOEiiRTtTSfQ5Saw0cYMYy45pB?usp=drive_link) folders and paste on the BUSCA root folder.

Edit the `precrisis_demo.py` file and replace its content with the content from the `busca/precrisis_demo.py` file in this repository.

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

#### LAVAD (Video Anomaly Detector)

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

#### Setup Pipeline

Copy `process_video.sh` and the `parsers` folder to the same folder where the repositories were cloned. Set up the following variables in the script:

```shell
BUSCA_DIR # path of the BUSCA source files
BUSCA_IMAGE_NAME # docker image name of BUSCA
AN_VIDEO_IMAGE_NAME # docker image name of the Video Anonymization
AN_VIDEO_DIR # path of the source code of the Video Anonymization
LAVAD_HOME_PATH # path of the LAVAD source code
```

# Executing Pipeline

To process one video in the pipeline, execute the following command:

```shell
./process_video.sh /raid/home/dvl/projects/vbezerra/precrisis_pipeline/test_videos/videos/cam_01_001.mp4 "04/18/24 13:00:00" "Mycity" "MyLocation" '"device=0,1"'
```

This command will generate an output folder called `cam_01_001_outputs` with the following content:

<pre>└── <font color="#12488B"><b>data</b></font>
    ├── bc.json
    ├── cp.json
    ├── cv.json
    ├── lavad.json
    └── <font color="#12488B"><b>videos</b></font>
        ├── <font color="#A347BA"><b>cam01001mp4_a.mp4</b></font>
        └── <font color="#A347BA"><b>cam01001mp4.mp4_busca.mp4</b></font>
</pre>

* `bc.json`: Results of BUSCA analysis in JSON format
* `cp.json`: Results of Crowd Panic analysis in JSON format
* `cv.json`: Results of Crowd Violence analysis in JSON format
* `lavad.json`: Results of LAVAD in JSON format
* `videos/cam_01_001_a.mp4`: Video output of LAVAD
* `videos/cam_01_001_busca.mp4`: Video output of BUSCA

# Insert into InfluxDB

Execute the following command, passing the output folder as a parameter:

```shell
python pipelines/video/influx/insert_data_influx.py ~/cam_01_001_outputs
```
