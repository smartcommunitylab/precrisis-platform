# VideoPlayback
## Setting Up

Create a `env` file following varibles for authentication:

```shell
GOOGLE_CLIENT_ID= CLIENT ID
GOOGLE_CLIENT_SECRET= CLIENT SECRET
GOOGLE_DISCOVERY_URL=https://aac.platform.smartcommunitylab.it/.well-known/openid-configuration
REDIRECT_URI= https://myurl/show/login/callback
LOGIN_URI= https://myurl/show/login
OAUTHLIB_INSECURE_TRANSPORT=1
EXTERNAL_URL= https://myurl/show
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