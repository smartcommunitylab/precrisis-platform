# VideoPlayback
## Setting Up

Create the following varibles for authentication:

```
GOOGLE_CLIENT_ID: Google client Id
GOOGLE_CLIENT_SECRET: Google client Secret
GOOGLE_DISCOVERY_URL: Google Discovery URL
EXTERNAL_URL: external address (https://example-videos.org/show)
```

Create a volume for storing the videos and mount on `/app/videos/`

## Build

```
docker build --pull --rm -f "Dockerfile" -t videoplayback:latest "."
```

## Run (Docker)
```
docker run -d -v /home/videos:/app/videos -p 5000:5000 videoplayback
```