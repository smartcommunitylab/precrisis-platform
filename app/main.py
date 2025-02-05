import streamlit as st
from influxdb import InfluxDBClient
import os
import base64

st.set_page_config(layout="wide")

@st.cache_resource
def get_database_session():
    client = InfluxDBClient(host=os.environ['INFLUXDB_HOST'], port=os.environ['INFLUXDB_PORT'], database=os.environ['INFLUXDB_DATABASE'])
    return client

if 'locations' not in st.session_state:
    result = get_database_session().query('select city,lat,long,location, thumb from locations;')
    ls = list(result.get_points())
    st.session_state.locations = ls
    st.session_state.current_location = ls[0]["location"]
    st.session_state.current_country = os.environ['COUNTRY']
    st.session_state.current_city = os.environ['CITY']

video = st.Page("pages/video.py", title="Video Analysis")
pos = st.Page("pages/pos.py", title="Places of Interest")
wm = st.Page("pages/wm.py", title="Warning Messages")
home = st.Page("pages/home.py", title="Home")
sp = st.Page("pages/sp.py", title="Safety Perception")
ur = st.Page("pages/ur.py", title="Urban Resiliency")
user_pages = [home, video, pos, ur, sp, wm]

pg = st.navigation(user_pages, position="hidden")


with st.sidebar:
    st.image("https://precrisis-project.eu/wp-content/uploads/2021/07/precrisis.svg")
    st.page_link("pages/home.py", label="Home")
    st.page_link("pages/video.py", label="Video Analysis")
    st.page_link("pages/pos.py", label="Places of Interest")
    st.page_link("pages/ur.py", label="Urban Resiliency")
    st.page_link("pages/sp.py", label="Safety Perception")
    st.page_link("pages/wm.py", label="Warning Messages")


    location_container = st.container()

    place = st.radio("Locations", [x["location"] for x in st.session_state.locations])
    st.session_state.current_location = place
    location_container.header(place)
    location = [x for x in st.session_state.locations if x["location"] == place][0]
    location_container.image(base64.decodebytes(bytes(location["thumb"], "utf-8")))
    
pg.run()
