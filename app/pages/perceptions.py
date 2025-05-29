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
    # ls = list(get_database_session().query('SELECT "score", "emotion" FROM "emotions" WHERE ("city"::tag = \'Vienna\' AND "location"::tag =~ /^' + st.session_state.current_location + '$/)'))
    # return ls[0]
    url = f"../data/perception/{st.session_state.current_city.lower()}/{st.session_state.current_city.lower()}-emotion-distribution.json"
    emotions = ["anger", "joy", "sadness", "fear"] if st.session_state.current_city != "Limassol" else ["Happyness", "Anger", "Sadness", "Surprise", "Fear", "Disgust"]
    with open(url, "r") as file:
        j = json.load(file)
        res = []
        for idx in range(len(j[st.session_state.current_location])):
            # res[emotions[idx]] = j[st.session_state.current_location][idx]
            res.append({"emotion": emotions[idx], "score": j[st.session_state.current_location][idx]})
        return res
    


def get_emotions_svg():
    url = f"../data/perception/{st.session_state.current_city.lower()}/piecharts/{st.session_state.current_city.lower()}_{st.session_state.current_location}_emotion_piechart.svg"
    with open(url, "r") as image_file:
        return image_file.read()
        # encoded_string = base64.b64encode(image_file.read())
        # return encoded_string.decode('utf-8')

def get_wordcloud():
    ls = list(get_database_session().query('SELECT "image" FROM "wordclouds" WHERE ("location"::tag =~ /^' + st.session_state.current_location + '$/)'))
    return ls[0]

def get_wordcloud_pos_img():
    url = f"../data/perception/{st.session_state.current_city.lower()}/wordclouds/{st.session_state.current_city}_{st.session_state.current_location}_positive.png"
    with open(url, "rb") as image_file:
        return image_file.read()

def get_wordcloud_neg_img():
    url = f"../data/perception/{st.session_state.current_city.lower()}/wordclouds/{st.session_state.current_city}_{st.session_state.current_location}_negative.png"
    with open(url, "rb") as image_file:
        return image_file.read()

def get_summary():
    url = f"../data/perception/{st.session_state.current_city.lower()}/summaries/{st.session_state.current_city.lower()}_{st.session_state.current_location}_top_sentiment.json"
    with open(url, "r") as file:
        summary = json.load(file)
        return summary['positive_summarization'], summary['negative_summarization']



def get_pois_list():
    ls = list(get_database_session().query('select Classification as SClassification, ID as SID, Keywords as Keywords, lat as slat, lon as slon from safety_perception').get_points())
    return ls
def get_pois(ls, types=['Safe', 'Unsafe']):
    res = {"type": "FeatureCollection", "features": []}
    colors = {'Safe': [25, 115, 14], 'Unsafe': [224, 47, 68]}
    res['features'] = [{"type": "Feature", "properties": {"v": x["Keywords"], "color": colors[x["SClassification"]]}, "geometry": {"type": "Point", "coordinates": [x["slon"], x["slat"]]}, "id": "poi"+str(i), "keywords": x["Keywords"], "type": "poi"} for i,x in enumerate(ls) if x["SClassification"] in types]  
    return res


# PAGE

# asyncio.run(init())
style = '''
<style>
div[data-testid="stMainBlockContainer"] {padding: 3rem 5rem 5rem 5rem !important;}
span[aria-label="Safe, close by backspace"] {background-color: rgb(25, 115, 14)}
span[aria-label="Unsafe, close by backspace"] {background-color: rgb(224, 47, 68)}
</style>
'''
st.markdown(style, unsafe_allow_html=True)

st.header('Perceptions Layer: '+ st.session_state.current_location.replace("_", " "))

with st.expander("Social Media Analysis", expanded=True):
    st.write("This section shows the textual analysis of social media posts about the selected area.")

    c1, c2, c3 = st.columns(3, vertical_alignment="top")
    pos, neg = get_summary()

    with c1:
        st.subheader("Emotion distribution")
        st.write("*Distribution of emotions expressed in social media posts about this location, indicated as the percentage of posts that express each emotion.*")
        # buff = bytes(get_emotions_img(), "utf-8")
        # st.image(get_emotions_svg())
        df = pd.DataFrame.from_records(get_emotions())
        print(df)
        fig = px.pie(df, values='score', names='emotion', color_discrete_sequence=px.colors.sequential.Oranges)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Positive posts word cloud")
        st.write("*Words that are more common in positive social media posts concerning this location.*")
        st.image(get_wordcloud_pos_img())
        st.subheader("Summary of positive aspects")
        st.write("*Summaries of positive aspects mentioned in social media posts about this location.*")
        st.write(pos)
        # st.image(base64.decodebytes(bytes(get_wordcloud()[0]["image"], "utf-8")))

    with c3:
        st.subheader("Negative posts word cloud")
        st.write("*Words that are more common in negative social media posts concerning this location.*")
        st.image(get_wordcloud_neg_img())
        st.subheader("Summary of negative aspects")
        st.write("*Summaries of negative aspects mentioned in social media posts about this location.*")
        st.write(neg)
        # st.image(base64.decodebytes(bytes(get_wordcloud()[0]["image"], "utf-8")))
    
    st.subheader("Topic Analysis")
    st.write("*Main topics that are discussed on social media posts about this location, extracted automatically. Each post is represented as a dot, the color of the dot indicates the topic discussed in the post. You can hover over the dots to read (pseudonymized) posts.*")
    # components.iframe("https://precrisis.smartcommunitylab.it/show/plot/" + st.session_state.current_location + "_2dim_embeddingSpace-new.html", height=770, scrolling=True)
    components.iframe(f"https://precrisis.smartcommunitylab.it/show/plot/{st.session_state.current_city.lower()}_{st.session_state.current_location}_new-embeddingspace-2d.html", height=770, scrolling=True)

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
current_location = [x for x in st.session_state.locations if x["location"] == st.session_state.current_location][0]
INITIAL_VIEW_STATE = pdk.data_utils.compute_view(poi_df[["lng", "lat"]]) 

selected_tags = st.multiselect("Safety perception", ["Safe", "Unsafe"], label_visibility="collapsed", default=["Safe", "Unsafe"])
pois = get_pois(poi_list, selected_tags)

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
    # tooltip={"html": '{v} <br> <img src="http://localhost:8501/media/f42afbbfb6ff8685cdb944530356e1bef387b91bd99659536d8b87a1.png" width="100">'}
    tooltip={"html": '{v}'}
)
st.pydeck_chart(r, use_container_width=True)
