# Grafana config

Edit `grafana.ini` and configure the Oauth configuration in the end of the file. Then build the image with the following command:

```bash
docker build -t grafana-precrisis .
```

To execute container execute:

```bash
docker run -d -p 3000:3000 --name=grafana --volume grafana-storage:/var/lib/grafana grafana-precrisis

docker update --restart unless-stopped $(docker ps -q)
```

The volume `grafana-storage` is located at: `/var/lib/docker/volumes/grafana-storage/_data`