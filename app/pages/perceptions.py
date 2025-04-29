import streamlit as st
from influxdb import InfluxDBClient

import pandas as pd
import streamlit.components.v1 as components
import json
import base64

import plotly.express as px

import pydeck as pdk

from geopy.geocoders import Nominatim
from math import radians, cos, sin, asin, sqrt

import asyncio

import osmnx
import networkx as nx
import os

@st.cache_resource
def get_database_session():
    client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST', "localhost"), port=os.getenv('INFLUXDB_PORT', 8086), database=os.getenv('INFLUXDB_DATABASE', 'precrisis'))
    return client


@st.cache_resource
def get_graph():
    graph = osmnx.graph_from_place(f"{st.session_state.current_city}, {st.session_state.current_country}", network_type = 'drive')
    # graph = osmnx.project_graph(graph)
    return graph

async def get_graph_async():
    return get_graph()

async def init():
    await get_graph_async()

def get_poi_df(pois):
    df = pd.DataFrame.from_records(pois)
    if df.empty: return df
    return df[["id", "v"]]

def get_pois(types, radius, colors):
    res = {"type": "FeatureCollection", "features": []}
    for type in types:
        color = colors[type]
        ls = list(get_database_session().query('SELECT * FROM "points_of_interest" WHERE ("location"::tag =~ /^' + st.session_state.current_location + '$/' + (' AND "radius"::tag = \''+str(radius)+'\'' if radius else '')+' AND "poi_type"::tag = \''+type+'\')').get_points())
        res['features'] = res['features'] + [{"type": "Feature", "properties": {"v": 1, "color": color, "fill_color": color + [70]}, "geometry": json.loads(x["geojson"]), "id": type+str(i), "v": type} for i,x in enumerate(ls)]
    return res        

def get_alerts():
    res = {"type": "FeatureCollection", "features": []}
    ls = list(get_database_session().query('SELECT "lat", "long",  "location", "score", "camera"  FROM "alerts"').get_points())
    res['features'] = [{"type": "Feature", "properties": {"v": x["location"], "color": [255,0,0], "fill_color": [255,0,0,70]}, "geometry": {"type": "Point", "coordinates": [x["long"], x["lat"]]}, "id": "alert"+str(i), "type": "alert"} for i,x in enumerate(ls)]    
    return res

def get_emotions():
    ls = list(get_database_session().query('SELECT "score", "emotion" FROM "emotions" WHERE ("city"::tag = \'Vienna\' AND "location"::tag =~ /^' + st.session_state.current_location + '$/)'))
    return ls[0]

def get_wordcloud():
    ls = list(get_database_session().query('SELECT "image" FROM "wordclouds" WHERE ("location"::tag =~ /^' + st.session_state.current_location + '$/)'))
    return ls[0]

def search_address(address):
    geolocator = Nominatim(user_agent="precrisis")
    str = f"{address}, {st.session_state.current_city}, {st.session_state.current_country}"
    res = geolocator.geocode(str)
    if res:
        return {"latitude": res.latitude, "longitude": res.longitude}
    else:
        return None


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r

def find_shortest_path(graph, location_orig, location_dest, optimizer):
    # find the nearest node to the departure and arrival location
    node_orig = osmnx.nearest_nodes(graph, location_orig[0], location_orig[1])
    node_dest = osmnx.nearest_nodes(graph, location_dest[0], location_dest[1])
    route = nx.shortest_path(graph, node_orig, node_dest, weight=optimizer.lower())
    route = osmnx.routing.route_to_gdf(graph, route, weight='length')
    route = osmnx.projection.project_gdf(route, to_latlong=True)
    route = json.loads(route.to_json(to_wgs84=True))
    return route

def shortest(location, pois):
    res = {}
    res_dist = {}
    for p in pois["features"]:
        t = p["v"]
        l = p["geometry"]["coordinates"] if p["geometry"]["type"] == "Point" else p["geometry"]["coordinates"][0][0]
        dist = haversine(location["longitude"], location["latitude"], l[0], l[1])
        if t not in res_dist:
            res_dist[t] = dist
            res[t] = l
        else: 
            if dist < res_dist[t]:
                res_dist[t] = dist
                res[t] = l
    g = get_graph()
    for t in res:
        res[t] = find_shortest_path(g, [location["longitude"], location["latitude"]], res[t], "length")
    # print(res)
    return res


def get_pois_list():
    ls = list(get_database_session().query('select Classification as SClassification, ID as SID, Keywords as Keywords, lat as slat, lon as slon from safety_perception').get_points())
    return ls
def get_pois(ls):
    res = {"type": "FeatureCollection", "features": []}
    colors = {'Safe': [25, 115, 14], 'Unsafe': [224, 47, 68]}
    res['features'] = [{"type": "Feature", "properties": {"v": x["Keywords"], "color": colors[x["SClassification"]]}, "geometry": {"type": "Point", "coordinates": [x["slon"], x["slat"]]}, "id": "poi"+str(i), "keywords": x["Keywords"], "type": "poi"} for i,x in enumerate(ls)]    
    return res


# PAGE

# asyncio.run(init())

st.header(st.session_state.current_location.replace("_", " "))

with st.expander("Social Media Analysis", expanded=True):
    st.write("This section shows the textual analysis of social media posts about the selected area.")

    c1, c2 = st.columns(2, vertical_alignment="top")

    with c1:
        st.subheader("Emotions")
        st.write("Distribution of emotions expressed in social media posts about the selected area.")
        df = pd.DataFrame.from_records(get_emotions())
        fig = px.pie(df, values='score', names='emotion')
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Negative Emotions Word Cloud")
        st.write("Most relevant words in posts associated with anger, disgust, fear and sadness.")
        st.image(base64.decodebytes(bytes(get_wordcloud()[0]["image"], "utf-8")))

    
    st.subheader("Topic Analysis")
    st.write("Topics discussed in social media posts about the selected area.")
    components.iframe("https://precrisis.smartcommunitylab.it/show/plot/" + st.session_state.current_location + "_2dim_embeddingSpace-new.html", height=770, scrolling=True)

st.header("Safety Perception")

st.write("""
        This submodule utilizes cutting-edge multi-modal AI models—specifically, Llava 1.6—to
        assess perceived safety across urban environments. The images used for analysis are
         primarily sourced from NUS Global Streetscapes ([Hou et al., 2024](https://doi.org/10.1016/j.isprsjprs.2024.06.023)), a widely recognized
         open-access dataset containing millions of images of public spaces from cities around the
         world. In some cases, images are also provided directly by project partners.

        Each image in the dataset is accompanied by a safety perception score, derived from human
        survey responses. The AI model is trained on this data to learn how to predict whether a
        given location appears safe or unsafe based solely on its visual features.
        
        The interactive map in this submodule displays available locations within the user-selected
        city. Each point on the map represents an image and is color-coded:
        - :green[Green] points indicate locations the AI model perceives as safe.
        - :red[Red] points represent locations considered unsafe.
         
        Users can hover over any point to view descriptive keywords generated by the AI model that
        explain its perception. For instance, safe areas may be associated with positive attributes like
        cleanliness, orderliness, or the absence of visible threats or neglect.
         """)
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
