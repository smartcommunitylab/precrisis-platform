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
    client = InfluxDBClient(host=os.environ['INFLUXDB_HOST'], port=os.environ['INFLUXDB_PORT'], database=os.environ['INFLUXDB_DATABASE'])
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


# PAGE

# asyncio.run(init())

st.header(st.session_state.current_location)

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


c1, c2 = st.columns(2)

with c1:
    st.subheader("Points of Interest")
    st.write(
        """
        This map visualizes the location of the points of interest within the selected radius for the chosen location. Points of interest, among others, include commercial activities, schools, cultural and political institutions and the location of leisure activities.
        """)


with c2:
    radius = st.selectbox('Radius', [500, 800, 1000, 4000])
    zoom = 14 if radius == 500 else 13 if radius == 800 else 12 if radius == 1000 else 10

current_location = [x for x in st.session_state.locations if x["location"] == st.session_state.current_location][0]
INITIAL_VIEW_STATE = pdk.ViewState(latitude=current_location["lat"], longitude=current_location["long"], zoom=zoom, pitch=0)

color_discrete_map={"buildings": [237,28, 33], "pois_gdf": [120, 167, 254]}
pois = get_pois(["pois_gdf", "buildings"], radius, color_discrete_map)

geojson = pdk.Layer(
    "GeoJsonLayer",
    pois,
    opacity=1,
    stroked=True,
    filled=True,
    extruded=False,
    wireframe=False,
    get_fill_color="properties.fill_color",
    get_line_color="properties.color",
)
r = pdk.Deck(
    layers=[geojson],
    initial_view_state=INITIAL_VIEW_STATE,
    map_provider="mapbox",
    map_style=None
)
st.pydeck_chart(r, use_container_width=True)


with st.expander("Street Network", expanded=True):
    st.write("The maps below visualize three types of street networks within the selected radius for the chosen location. The specific types are: Pedestrian networks (blue), Vehicle networks (red), Bike networks (green).")

    tags = ["pedestrian_streets", "vehicle_streets", "bike_streets"]
    colors = {"pedestrian_streets": [40, 93, 208], "vehicle_streets": [213, 24, 52], "bike_streets": [23, 101, 13]}
    pois = get_pois(tags, radius, colors)

    geojson = pdk.Layer(
        "GeoJsonLayer",
        pois,
        pickable=True,
        point_type=pdk.types.String('text'),
        stroked=True,
        get_line_color="properties.color",
        get_fill_color=[160, 160, 180, 200],
        line_width_units=pdk.types.String('pixels'),
        get_line_width=3,
        get_text="properties.color",
        auto_highlight=True,
        get_text_size=12
    )
    r = pdk.Deck(
        layers=[geojson],
        initial_view_state=INITIAL_VIEW_STATE,
        map_provider="mapbox",
        map_style=None,
        tooltip={"text": "{v}"}
    )
    st.pydeck_chart(r, use_container_width=True)


tags = ["hospitals", "police", "fire_station"]
colors = {"police": [40, 93, 208], "hospitals": [213, 24, 52], "fire_station": [221, 117, 47]}
pois = get_pois(tags, None, colors)
with st.expander("Services", expanded=True):
    st.write("The maps below visualize three types of services within the selected radius for the chosen location. The specific service types are: Hospitals (red), Police Stations (blue) and Fire Stations (orange)")

    # print(pois)
    geojson = pdk.Layer(
        "GeoJsonLayer",
        pois,
        pickable=True,
        point_type=pdk.types.String('circle+text'),
        stroked=True,
        filled=True,
        get_line_color="properties.color",
        get_fill_color="properties.fill_color",
        line_width_units=pdk.types.String('pixels'),
        get_point_radius=3,
        point_radius_units=pdk.types.String('pixels'),
        get_line_width=3,
        get_text="properties.color",
        auto_highlight=True,
        get_text_size=12
    )
    view = pdk.ViewState(latitude=current_location["lat"], longitude=current_location["long"], zoom=11, pitch=0)
    r = pdk.Deck(
        layers=[geojson],
        initial_view_state=view,
        map_provider="mapbox",
        map_style=None,
        tooltip={"text": "{v}"},
    )
    st.pydeck_chart(r, use_container_width=True)


with st.expander("Shortest Paths", expanded=True):
    st.write(
        """
        The maps below visualize the shortest paths for the closest services. 
        The map shows: the shortest path to the nearest hospital, the shortest path to the nearest police station and the shortest path to the nearest fire station.
        To use this feature, please search for an address or cl ick on one of the Alert circles.
        """)

    geojson = pdk.Layer(
        "GeoJsonLayer",
        pois,
        pickable=False,
        point_type=pdk.types.String('circle+text'),
        stroked=True,
        filled=True,
        get_line_color="properties.color",
        get_fill_color="properties.fill_color",
        line_width_units=pdk.types.String('pixels'),
        get_point_radius=3,
        point_radius_units=pdk.types.String('pixels'),
        get_line_width=3,
        get_text="properties.color",
        auto_highlight=True,
        get_text_size=12
    )
    alerts = get_alerts()
    alert_layer = pdk.Layer(
        "GeoJsonLayer",
        alerts,
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
        get_text_size=12
    )
    layers = [geojson, alert_layer]

    def render_from_location(location, layers):
        print(location)
        if location is not None:
            df = pd.DataFrame([{"lat": location["latitude"], "lon": location["longitude"], "coordinates": [location["longitude"], location["latitude"]]}])
            layer = pdk.Layer(
                "ScatterplotLayer",
                pickable=False,
                data=df,
                opacity=1,
                get_position="[lon, lat]",
                get_color="[58, 145, 68]",
                get_radius=8,
                radius_units=pdk.types.String('pixels'),
            ),
            layers.append(layer)

            shortest_dict = shortest(location, pois)
            for k in shortest_dict:
                layer = pdk.Layer(
                    "GeoJsonLayer",
                    shortest_dict[k],
                    pickable=False,
                    stroked=True,
                    filled=True,
                    get_line_color=colors[k],
                    line_width_units=pdk.types.String('pixels'),
                    get_line_width=3,
                    auto_highlight=True
                )
                layers.append(layer)

            state = pdk.ViewState(latitude=location["latitude"], longitude=location["longitude"], zoom=11, pitch=0)
        else: 
            state = pdk.ViewState(latitude=current_location["lat"], longitude=current_location["long"], zoom=12, pitch=0)

        r = pdk.Deck(
            layers=layers,
            initial_view_state=state,
            map_provider="mapbox",
            map_style=None,
            tooltip={"text": "{v}"},
        )
        st.pydeck_chart(r, use_container_width=True, on_select="rerun", selection_mode="single-object", key="shortest")

    def on_select():
        if st.session_state.shortest is None or len(st.session_state.shortest["selection"]["objects"].values()) == 0:
            render_from_location(None, [geojson, alert_layer])
        else: 
            print(st.session_state.shortest)
            coords = list(st.session_state.shortest["selection"]["objects"].values())[0][0]["geometry"]["coordinates"]
            obj = {"latitude": coords[1], "longitude": coords[0]}
            render_from_location(obj, [geojson, alert_layer])

    address = st.text_input("Address", "")
    if st.button("Search"):
        # st.session_state.shortest = None
        location = search_address(address)
        if location is None:
            st.write("Address not found")
        render_from_location(location, [geojson, alert_layer])
    elif 'shortest' in st.session_state:           
        on_select()
    else:    
        render_from_location(None, [geojson, alert_layer])
