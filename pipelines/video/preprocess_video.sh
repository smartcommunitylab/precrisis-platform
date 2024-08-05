#!/bin/bash

# Step 0: get work directory and variables
dir=$(pwd)
workdir="${dir}/tmp"

RECORDING_DATE="04/18/24 13:00:00"
CITY="Vienna"
LOCATION=""
CAMERA_NAME=""

# Step 1: Rename file

# Check if exactly one argument (filename) is provided
if [ $# -ne 1 ]; then
  echo "Usage: $0 <filename>"
  exit 1
fi

# Get the filename from the argument
filename="$1"

# Function to remove special characters and lowercase the filename
sanitize_filename() { basename "${1}" | tr -d '[[:punct:] ]' | tr '[:upper:]' '[:lower:]'; }

# Get the cleaned filename
# filename="My File Name.with.special$char.txt"
sanitized_name=$(sanitize_filename "$filename")

sanitized_name="${sanitized_name}.mp4"

mkdir "$workdir"

# Check if the file exists
if [ ! -f "$filename" ]; then
  echo "Error: File '$filename' does not exist."
  exit 1
fi

# copy and replace name
cp "$filename" "$workdir"/"$sanitized_name"

echo "File renamed to: $sanitized_name"

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

python3 parsers/certh_cp_precrisis.py 

# remove trash

rm -r "$workdir"/Uploads

# Crowd Violence

# create folders

mkdir "$workdir"/videos

mkdir "$workdir"/outputs

cp "$workdir"/"$sanitized_name" "$workdir"/videos

docker run -it -v "$workdir"/videos:/app/Input_videos -v "$workdir"/outputs:/app/Output --gpus '"device=1,2"' --rm certh_ca_ma_demo:0.0.6

python3 parsers/certh_cv_precrisis.py

rm -r "$workdir"/videos
rm -r "$workdir"/outputs

