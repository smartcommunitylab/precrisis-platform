# Precrisis UI

The Precrisis platform UI is implemented with the Streamlit framework relying on the data and metadata produced and prepared during the analysis and preprocessing phases.

## Requirements

To run the app, the [Streamlit](https://streamlit.io/) framework should be installed.  See [full list of requirements](../app/requirements.txt) to be installed.

The application relies on the data made available in the form of Influx DB and files resulting from the elaborations. More specifically,

- Influx DB with the collections representing the necessary video-related data (``object_tracker``, ``video_busca``, ``video_anomaly_score``, ``crowd_violence``, ``panic_module``, ``panic_module_clips``, ``alerts``), points of interests (``points_of_interest``), safety perception data (``safety_perception``), and reference locations ``locations``;
- location thumbnails (``data/thumbs/`` folder);
- perception data (``data/perception/<city>/`` folder) with piecharts, emotion distribution data JSON files, wordclouds and summaries.

The configuration of the application relies on the following environment variables

- ``SERVER_URL``: the address of the videoplayback server
- ``INFLUXDB_HOST``, ``INFLUXDB_PORT``, ``INFLUXDB_DATABASE`` to configure the host, port and database name.
- ``DATA_PATH``: path to the data needed for the visualization (defaults to ``../data``).
- ``COUNTRY`` and ``CITY`` to configure the app context.

## Installation

To run the application use the following script

```bash
streamlit run app/main.py
```
Pass or set the environment variables before the execution of the script.

To run the application with Docker, build the image from the app folder

```bash
docker build -t precrisis-ui .
```

and run the application
```bash
docker run -d --restart=always -p 8501:8501 -v /home/precrisis/platform/data:/data  --env-file ./.env precrisis-ui
```

The application is available at ``http://localhost:8501/``.





