import streamlit as st
from influxdb import InfluxDBClient

import pandas as pd

import pydeck as pdk
import os

@st.cache_resource
def get_database_session():
    client = InfluxDBClient(host=os.environ['INFLUXDB_HOST'], port=os.environ['INFLUXDB_PORT'], database=os.environ['INFLUXDB_DATABASE'])
    return client

def get_pois_list():
    ls = list(get_database_session().query('select Classification as SClassification, ID as SID, Keywords as Keywords, lat as slat, lon as slon from safety_perception').get_points())
    return ls
def get_pois(ls):
    res = {"type": "FeatureCollection", "features": []}
    colors = {'Safe': [25, 115, 14], 'Unsafe': [224, 47, 68]}
    res['features'] = [{"type": "Feature", "properties": {"v": x["Keywords"], "color": colors[x["SClassification"]]}, "geometry": {"type": "Point", "coordinates": [x["slon"], x["slat"]]}, "id": "poi"+str(i), "keywords": x["Keywords"], "type": "poi"} for i,x in enumerate(ls)]    
    return res

st.header("Safety Perception")

poi_list = get_pois_list()
poi_df = pd.DataFrame.from_records([x for x in poi_list ]).rename(columns={"slat": "lat", "slon": "lng"})
pois = get_pois(poi_list)
current_location = [x for x in st.session_state.locations if x["location"] == st.session_state.current_location][0]
INITIAL_VIEW_STATE = pdk.data_utils.compute_view(poi_df[["lng", "lat"]]) 

geojson = pdk.Layer(
        "GeoJsonLayer",
        pois,
        pickable=True,
        point_type=pdk.types.String('circle+text'),
        stroked=True,
        filled=True,
        get_line_color="properties.color",
        get_fill_color="properties.color",
        line_width_units=pdk.types.String('pixels'),
        get_point_radius=5,
        point_radius_units=pdk.types.String('pixels'),
        get_line_width=3,
        get_text="properties.color",
        auto_highlight=True,
        get_text_size=10
    )
r = pdk.Deck(
    layers=[geojson],
    initial_view_state=INITIAL_VIEW_STATE,
    map_provider="mapbox",
    map_style=None,
    tooltip={"text": "{v}"}
)
st.pydeck_chart(r, use_container_width=True)
