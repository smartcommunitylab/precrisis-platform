#!/bin/bash

# Step 0: get work directory and variables
dir=$(pwd)

# processors paths
BUSCA_DIR="${dir}/BUSCA"
BUSCA_IMAGE_NAME="precrisis_busca-vbezerra-dsl-7:latest"
AN_VIDEO_DIR="/raid/home/dvl/projects/vbezerra/precrisis_pipeline/marvel-videoanony"

# video args
filename="$1"
RECORDING_DATE="04/18/24 13:00:00"
CITY="Vienna"
LOCATION="Austria"

# Step 1: Rename file and Anonymise

# Check if exactly one argument (filename) is provided
if [ $# -ne 1 ]; then
  echo "Usage: $0 <filename>"
  exit 1
fi

# Function to remove special characters and lowercase the filename
sanitize_filename() { basename "${1}" | tr -d '[[:punct:] ]' | tr '[:upper:]' '[:lower:]'; }

# Get the cleaned filename
sanitized_name=$(sanitize_filename "$filename")

sanitized_name_without_extension="${sanitized_name}"

sanitized_name="${sanitized_name}.mp4"

CAMERA="${sanitized_name}"

workdir="${dir}/${sanitized_name_without_extension}_outputs"

mkdir "$workdir"

# Check if the file exists
if [ ! -f "$filename" ]; then
  echo "Error: File '$filename' does not exist."
  exit 1
fi

# copy and replace name
cp "$filename" "$workdir"/"$sanitized_name"

echo "File renamed to: $sanitized_name"

# Anonymise

mkdir "$AN_VIDEO_DIR"/videos 

cp "$workdir"/"$sanitized_name" "$AN_VIDEO_DIR"/videos/"$sanitized_name"

# remove original file 

rm "$workdir"/"$sanitized_name"

docker run -it -v "$AN_VIDEO_DIR":/app -u `id -u $USER` --gpus all anonymisation-vbezerra-dsl-1 \
python src/anonymize.py --source videos/"$sanitized_name"

# replace video

cp -i "$AN_VIDEO_DIR"/runs/anonymize/exp/"$sanitized_name" "$workdir"/"$sanitized_name"

# cleanup

rm -r "$AN_VIDEO_DIR"/runs
rm -r "$AN_VIDEO_DIR"/videos

mkdir "$workdir"/data

# Step 2: run inference

# Crowd Panic

# create folders

mkdir "$workdir"/Uploads

# copy file to folder

cp "$workdir"/"$sanitized_name" "$workdir"/Uploads

# run inference

docker run -it --rm --gpus all \
    -p 8080:8080 \
    -v "$workdir"/Uploads:/usr/src/app/Uploads \
    -v "$workdir"/Uploads/"$sanitized_name":/usr/src/app/Uploads/"$sanitized_name" \
    certh_cv_precrisis_cpd --video_path /usr/src/app/Uploads/"$sanitized_name"

# remove original file from folder

rm "$workdir"/Uploads/"$sanitized_name"

# create influx files

python3 parsers/certh_cp_precrisis.py "${workdir}/Uploads/${sanitized_name}_panic_clips.json" "$CITY" "$CAMERA" "$LOCATION" "$RECORDING_DATE" "${workdir}/data"

# remove trash

rm -f -r "$workdir"/Uploads

# Crowd Violence

# create folders

mkdir "$workdir"/videos

mkdir "$workdir"/outputs

cp "$workdir"/"$sanitized_name" "$workdir"/videos

docker run -it -v "$workdir"/videos:/app/Input_videos -v "$workdir"/outputs:/app/Output --gpus '"device=1,2"' --rm certh_ca_ma_demo:0.0.6

python3 parsers/certh_cv_precrisis.py "${workdir}/outputs/${sanitized_name_without_extension}.json" "$CITY" "$CAMERA" "$LOCATION" "$RECORDING_DATE" "${workdir}/data"

rm -f -r "$workdir"/videos
rm -f -r "$workdir"/outputs

# BUSCA

# go to the busca folder

mkdir "$BUSCA_DIR"/videos 

cp "$workdir"/"$sanitized_name" "$BUSCA_DIR"/videos

docker run --gpus '"device=1,2"' \
 -it --rm -v "$BUSCA_DIR":/workspace/BUSCA \
 "$BUSCA_IMAGE_NAME" \
 python precrisis_demo.py --path videos/"$sanitized_name" --device gpu

mv "$BUSCA_DIR"/videos/"$sanitized_name" "$BUSCA_DIR"/videos/"$sanitized_name"_busca.mp4 

python3 parsers/fbk_bc_precrisis.py "${BUSCA_DIR}/BUSCA_OUTPUT/${sanitized_name}.json" "$CITY" "$CAMERA" "$LOCATION" "$RECORDING_DATE" "${workdir}/data"

rm -r "$BUSCA_DIR"/videos
rm -r "$BUSCA_DIR"/BUSCA_OUTPUT

# LAVAD

# docker run --shm-size 64gb --name lavad-lzanella-dvl-3-4 --gpus '"device=3,4"' --rm -it -v $(pwd):/usr/src/app -v /raid/home/dvl/projects/vbezerra/lavad/PRECRISIS_cams:/usr/src/datasets -v /raid/home/dvl/projects/lzanella/llama/:/raid/home/dvl/projects/lzanella/llama/ -v /raid/home/dvl/datasets/UCFCrime/Anomaly-Frames/:/raid/home/dvl/datasets/UCFCrime/Anomaly-Frames/ dvl/lavad /bin/bash

# VIDEO CONVERSION

mkdir "${workdir}/data/videos/"

cd "${workdir}/data/"

for i in *.mp4; do
  docker run -v $(pwd):$(pwd) -w $(pwd)\
          jrottenberg/ffmpeg:4.4-scratch -i "$i" -y videos/"$i"
  
  rm -f "$i"
done

cd "${dir}"