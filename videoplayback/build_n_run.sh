docker build --pull --rm -f "Dockerfile" -t videoplayback:latest "."
docker run -d -v /home/precrisis/videoplayback/videos:/app/videos -e env -p 5000:5000 videoplayback