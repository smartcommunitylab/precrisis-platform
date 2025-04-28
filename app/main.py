import streamlit as st
from influxdb import InfluxDBClient
import os
import base64
import pandas as pd

st.set_page_config(layout="wide")

@st.cache_resource
def get_database_session():
    client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST', "localhost"), port=os.getenv('INFLUXDB_PORT', 8086), database=os.getenv('INFLUXDB_DATABASE', 'precrisis'))
    return client

st.session_state.current_city = os.getenv('CITY', "Vienna")
st.session_state.current_country = os.getenv('COUNTRY', "Austria")

if 'locations' not in st.session_state:
    result = get_database_session().query(f"select city,lat,long,location, thumb from locations;")
    ls = list(result.get_points())
    ls.sort(key=lambda x: x["location"])

    # import pandas as pd
    # print(pd.DataFrame.from_records(ls))

    st.session_state.locations = ls
    st.session_state.current_location = ls[0]["location"]

    ls = list(get_database_session().query('SELECT "lat", "long",  "location", "score", "camera"  FROM "alerts"').get_points())
    alert_df = pd.DataFrame.from_records([x for x in ls ])
    alert_df = alert_df[["lat", "long", "location", "score", "camera"]].drop_duplicates().groupby(["lat", "long", "location", "camera"]).mean().reset_index()
    st.session_state.alert_location_names = alert_df[["location"]].drop_duplicates()['location'].tolist()


pos = st.Page("pages/urban.py", title="Urban Layer")
video = st.Page("pages/video.py", title="Human Dynamics Layer")
sp = st.Page("pages/perceptions.py", title="Perceptions Layer")
wm = st.Page("pages/wm.py", title="Counter-Action Layer")
home = st.Page("pages/home.py", title="Home")
user_pages = [home, pos, video, sp, wm]

pg = st.navigation(user_pages, position="hidden")


with st.sidebar:
    st.image("https://precrisis-project.eu/wp-content/uploads/2021/07/precrisis.svg")
    st.page_link("pages/home.py", label="Home")
    st.page_link("pages/urban.py", label="Urban Layer")
    st.page_link("pages/video.py", label="Human Dynamics Layer")
    st.page_link("pages/perceptions.py", label="Perceptions Layer")
    st.page_link("pages/wm.py", label="Counter-Action Layer")
    st.divider()


    location_container = st.container()
    def format_func(x):
        res = x["location"] + ':red[:material/error:]' if x["location"] in st.session_state.alert_location_names else x["location"]
        res = res.replace("_", " ")
        return res

    place = st.radio("Locations", [x for x in st.session_state.locations], format_func=format_func, index=0)
    st.session_state.current_location = place["location"]
    location_container.header("Selected Location")
    location_container.subheader(place['location'].replace("_", " "))
    location = [x for x in st.session_state.locations if x["location"] == place["location"]][0]
    location_container.image(base64.decodebytes(bytes(location["thumb"], "utf-8")), use_container_width=True)
    
pg.run()
