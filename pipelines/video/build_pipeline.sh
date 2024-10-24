#!/bin/bash
cd BUSCA/
./build.sh 
cd ..
cd certh/
docker load < certh_ca_violence_v2.tar 
docker load < certh_cv_precrisis_cpd_v2.tar 
cd ..
cd marvel-videoanony/
./build_gpu.sh 
cd ..
cd /raid/home/dvl/projects/vbezerra/lavad/
./scripts/docker_build.sh
cd -