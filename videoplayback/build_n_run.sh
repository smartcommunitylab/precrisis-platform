docker build --pull --rm -f "Dockerfile" -t videoplayback:latest "."
docker run -d -v /precrisis-platform/videoplayback/videos:/app/videos -p 5000:5000 videoplayback