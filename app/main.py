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

def get_thumb(name):
    url = f"../data/thumbs/{name}.jpg"
    with open(url, "rb") as image_file:
        return image_file.read()

if 'locations' not in st.session_state:
    result = get_database_session().query(f"select city,lat,long,location from locations;")
    ls = list(result.get_points())
    ls.sort(key=lambda x: x["location"])

    # import pandas as pd
    # print(pd.DataFrame.from_records(ls))

    st.session_state.locations = ls

    ls = list(get_database_session().query('SELECT "lat", "long",  "location", "score", "camera"  FROM "alerts"').get_points())
    alert_df = pd.DataFrame.from_records([x for x in ls ])
    alert_df = alert_df[["lat", "long", "location", "score", "camera"]].drop_duplicates().groupby(["lat", "long", "location", "camera"]).mean().reset_index()
    alert_names = alert_df[["location"]].drop_duplicates()['location'].tolist()
    alert_names.sort()
    st.session_state.alert_location_names = alert_names
    st.session_state.current_location = alert_names[0] if len(alert_names) > 0 else ls[0]["location"]
    st.session_state.current_location_index = st.session_state.locations.index([x for x in st.session_state.locations if x["location"] == st.session_state.current_location][0])


pos = st.Page("pages/urban.py", title="Urban Layer")
video = st.Page("pages/video.py", title="Human Dynamics Layer")
sp = st.Page("pages/perceptions.py", title="Perceptions Layer")
wm = st.Page("pages/wm.py", title="Counter-Action Layer")
home = st.Page("pages/home.py", title="Home")
user_pages = [home, pos, video, sp, wm]

pg = st.navigation(user_pages, position="hidden")


with st.sidebar:
    st.logo("https://precrisis-project.eu/wp-content/uploads/2021/07/precrisis.svg", size="large", link="https://precrisis-project.eu/")
    style = '''
    <style>
    img[data-testid="stLogo"]{height: 4rem;}
    </style>
    '''
    st.markdown(style, unsafe_allow_html=True)

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

    index = st.session_state.locations.index([x for x in st.session_state.locations if x["location"] == st.session_state.current_location][0])

    place = st.radio("Locations", [x for x in st.session_state.locations], format_func=format_func, index=st.session_state.current_location_index)
    st.session_state.current_location = place["location"]
    location_container.header("Selected Location")
    location_container.subheader(place['location'].replace("_", " "))
    location = [x for x in st.session_state.locations if x["location"] == place["location"]][0]
    # location_container.image(base64.decodebytes(bytes(location["thumb"], "utf-8")), use_container_width=True)
    location_container.image(get_thumb(location["location"]), use_container_width=True)
pg.run()
