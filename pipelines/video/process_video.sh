#!/bin/bash

# configurations
dir=$(pwd)

# processors paths
BUSCA_DIR="${dir}/BUSCA"
BUSCA_IMAGE_NAME="precrisis_busca-vbezerra-dsl-7:latest"
AN_VIDEO_IMAGE_NAME="anonymisation-vbezerra-dsl-1"
AN_VIDEO_DIR="/raid/home/dvl/projects/vbezerra/precrisis_pipeline/marvel-videoanony"
LAVAD_HOME_PATH="/raid/home/dvl/projects/vbezerra/lavad/"

# video args
filename="$1"
RECORDING_DATE="$2"
CITY="$3"
LOCATION="$4"
#CAMERA=Video File Name
GPU_DEVICE="$5"

if [ -z "$6" ]; then
  ANONYMISATION="True"
else
  ANONYMISATION="False"
fi

# video renaning and anonymisation

if [ ! -f "$filename" ]; then
  echo "Error: File '$filename' does not exist."
  exit 1
fi

start_time=$(date +%s)

echo "$(date +"%Y-%m-%d %H:%M:%S"): START PROCESSING $filename"

sanitize_filename() { basename "${1}" | tr -d '[[:punct:] ]' | tr '[:upper:]' '[:lower:]'; }

sanitized_name=$(sanitize_filename "$filename")

sanitized_name_without_extension="${sanitized_name}"

sanitized_name="${sanitized_name}.mp4"

CAMERA="${sanitized_name}"

if [[ "$ANONYMISATION" == "False" ]]; then
  workdir="${dir}/outputs/${sanitized_name_without_extension}_outputs_original"
else
  workdir="${dir}/outputs/${sanitized_name_without_extension}_outputs"
fi

# workdir creation

mkdir "$workdir"

mkdir "$workdir"/data

cp "$filename" "$workdir"/"$sanitized_name"

echo "File renamed to: $sanitized_name"

# anonymisation

if [[ "$ANONYMISATION" == "True" ]]; then

  echo "$(date +"%Y-%m-%d %H:%M:%S"): START ANONYMISATION $sanitized_name"

  mkdir "$AN_VIDEO_DIR"/videos 

  cp "$workdir"/"$sanitized_name" "$AN_VIDEO_DIR"/videos/"$sanitized_name"

  # remove original file 

  rm "$workdir"/"$sanitized_name"

  docker run -it -v "$AN_VIDEO_DIR":/app -u `id -u $USER` --gpus "$GPU_DEVICE" "$AN_VIDEO_IMAGE_NAME" \
  python src/anonymize.py --source videos/"$sanitized_name"

  cp -i "$AN_VIDEO_DIR"/runs/anonymize/exp/"$sanitized_name" "$workdir"/"$sanitized_name"

  rm -r "$AN_VIDEO_DIR"/runs
  rm -r "$AN_VIDEO_DIR"/videos

  echo "$(date +"%Y-%m-%d %H:%M:%S"): END ANONYMISATION $sanitized_name"
fi
# INFERENCE RUNNING

# Crowd Panic

echo "$(date +"%Y-%m-%d %H:%M:%S"): START CROWD_PANIC $sanitized_name"

mkdir "$workdir"/Uploads

cp "$workdir"/"$sanitized_name" "$workdir"/Uploads

docker run -it --rm --gpus "$GPU_DEVICE" \
    -p 8080:8080 \
    -v "$workdir"/Uploads:/usr/src/app/Uploads \
    -v "$workdir"/Uploads/"$sanitized_name":/usr/src/app/Uploads/"$sanitized_name" \
    certh_cv_precrisis_cpd --video_path /usr/src/app/Uploads/"$sanitized_name"

# remove original file from folder

rm "$workdir"/Uploads/"$sanitized_name"

python3 parsers/certh_cp_precrisis.py "${workdir}/Uploads/${sanitized_name}_panic_clips.json" "$CITY" "$CAMERA" "$LOCATION" "$RECORDING_DATE" "${workdir}/data"

# remove trash

rm -f -r "$workdir"/Uploads

echo "$(date +"%Y-%m-%d %H:%M:%S"): END CROWD_PANIC $sanitized_name"

# Crowd Violence

echo "$(date +"%Y-%m-%d %H:%M:%S"): START CROWD_VIOLENCE $sanitized_name"

mkdir "$workdir"/videos

mkdir "$workdir"/outputs

cp "$workdir"/"$sanitized_name" "$workdir"/videos

docker run -it -v "$workdir"/videos:/app/Input_videos -v "$workdir"/outputs:/app/Output --gpus "$GPU_DEVICE" --rm certh_ca_ma_demo:0.0.6

python3 parsers/certh_cv_precrisis.py "${workdir}/outputs/${sanitized_name_without_extension}.json" "$CITY" "$CAMERA" "$LOCATION" "$RECORDING_DATE" "${workdir}/data"

rm -f -r "$workdir"/videos
rm -f -r "$workdir"/outputs

echo "$(date +"%Y-%m-%d %H:%M:%S"): END CROWD_VIOLENCE $sanitized_name"

# BUSCA

echo "$(date +"%Y-%m-%d %H:%M:%S"): START BUSCA $sanitized_name"

mkdir "$BUSCA_DIR"/videos 

cp "$workdir"/"$sanitized_name" "$BUSCA_DIR"/videos

docker run --gpus "$GPU_DEVICE" \
 -it --rm -v "$BUSCA_DIR":/workspace/BUSCA \
 "$BUSCA_IMAGE_NAME" \
 python precrisis_demo.py --path videos/"$sanitized_name" --device gpu

mv "$BUSCA_DIR"/BUSCA_OUTPUT/"$sanitized_name" "$BUSCA_DIR"/BUSCA_OUTPUT/"$sanitized_name"_busca.mp4 

python3 parsers/fbk_bc_precrisis.py "${BUSCA_DIR}/BUSCA_OUTPUT/${sanitized_name}.json" "$CITY" "$CAMERA" "$LOCATION" "$RECORDING_DATE" "${workdir}/data"

rm -r "$BUSCA_DIR"/videos
rm -r "$BUSCA_DIR"/BUSCA_OUTPUT

echo "$(date +"%Y-%m-%d %H:%M:%S"): END BUSCA $sanitized_name"

# LAVAD

echo "$(date +"%Y-%m-%d %H:%M:%S"): START LAVAD $sanitized_name"

mkdir -p "${workdir}"/lavad_video/precrisis/videos/

cp "$workdir"/"$sanitized_name" "${workdir}"/lavad_video/precrisis/videos/

mkdir -p "${workdir}"/lavad_video/precrisis/annotations/

docker run --shm-size 64gb --gpus "$GPU_DEVICE" --rm -it -u `id -u $USER` -v "$LAVAD_HOME_PATH":/usr/src/app -v "${workdir}"/lavad_video:/usr/src/datasets lavad ./scripts/run_eval.sh

LAVAD_OUTPUT="${workdir}/lavad_video/precrisis/scores/refined/llama-2-13b-chat/opt-6.7b-coco+opt-6.7b+flan-t5-xxl+flan-t5-xl+flan-t5-xl-coco/000001_if_you_were_a_law_enforcement_agency,_how_would_you_rate_the_scene_described_on_a_scale_from_0_to_1,_with_0_representing_a_standard_scene_and_1_denoting_a_scene_with_suspicious_activities?"

cp "$LAVAD_OUTPUT"/"$sanitized_name" "${workdir}/data/${sanitized_name_without_extension}_a.mp4"

python3 parsers/fbk_lavad_precrisis.py "${LAVAD_OUTPUT}/${sanitized_name_without_extension}.json" "$CITY" "$CAMERA" "$LOCATION" "$RECORDING_DATE" "${workdir}/data"

rm -r "${workdir}"/lavad_video

echo "$(date +"%Y-%m-%d %H:%M:%S"): END LAVAD $sanitized_name"

# INFERENCE RUNNING

# REMOVE ORIGINAL FILE

rm "$workdir"/"$sanitized_name"

# VIDEO CONVERSION
echo "$(date +"%Y-%m-%d %H:%M:%S"): START VIDEO_CONVERSION $sanitized_name"

mkdir "${workdir}/data/videos/"

cd "${workdir}/data/"

for i in *.mp4; do
  docker run -v $(pwd):$(pwd) -w $(pwd)\
          jrottenberg/ffmpeg:4.4-scratch -i "$i" -y videos/"$i"
  
  rm -f "$i"
done

cd "${dir}"

echo "$(date +"%Y-%m-%d %H:%M:%S"): END VIDEO_CONVERSION $sanitized_name"

echo "$(date +"%Y-%m-%d %H:%M:%S"): END PROCESSING $filename"

finish_time=$(date +%s)

elapsed_time=$((finish_time  - start_time))

((sec=elapsed_time%60, elapsed_time/=60, min=elapsed_time%60, hrs=elapsed_time/60))
timestamp=$(printf "Total time taken - %d hours, %d minutes, and %d seconds." $hrs $min $sec)
echo $timestamp