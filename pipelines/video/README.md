# Process Data for Video Analysis

## Installation

### DGX1 FBK

If running on the DGX1, navigate to `dvl/projects/vbezerra/precrisis_pipeline/` and run the `build_pipeline.sh` script.

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

Download [model_busca.pth](https://drive.google.com/file/d/1jRYMVOc5wid9paCgJdEd3RhSxBC32O2h/view?usp=sharing) and store it in `models/BUSCA/motsynth/`.
Download [model_feats.pth](https://drive.google.com/file/d/1ZNU0yNkhMTlLRSOC0PR82SwK1ic9OJ8Y/view?usp=sharing) and store it in `models/feature_extractor/market1501/`.
Download [bytetrack_x_mot17.pth.tar](https://drive.google.com/file/d/1P4mY0Yyd3PPTybgZkjMYhFri88nTmJX5/view?usp=sharing) and store it in `pretrained/`.

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

## Executing Pipeline

