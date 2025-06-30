import streamlit as st
from influxdb import InfluxDBClient

import pandas as pd
import geopandas as gpd
import streamlit.components.v1 as components
import json
import base64

import plotly.express as px

import pydeck as pdk

from geopy.geocoders import Nominatim
from math import radians, cos, sin, asin, sqrt

import folium
from streamlit_folium import st_folium

import osmnx
import networkx as nx
import os


@st.cache_resource
def get_database_session():
    client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST', "localhost"), port=os.getenv('INFLUXDB_PORT', 8086), database=os.getenv('INFLUXDB_DATABASE', 'precrisis'))
    return client


@st.cache_resource
def get_graph():
    place = f"{st.session_state.current_city}, {st.session_state.current_country}"
    print(place)
    if st.session_state.current_city == "Sofia":
        place = "Sofia, Sredec, Sofia City, Sofia-City, Bulgaria"

    graph = osmnx.graph_from_place(place, network_type = 'drive')
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

def type_to_label(type):
    if type == "pois_gdf":
        return "Points of Interest"
    elif type == "buildings":
        return "Building"
    elif type == "pedestrian_streets":
        return "Pedestrian Street"
    elif type == "vehicle_streets":
        return "Vehicle Street"
    elif type == "bike_streets":
        return "Bike Street"
    elif type == "hospitals":
        return "Hospital"
    elif type == "police":
        return "Police Station" 
    elif type == "fire_station":
        return "Fire Station"
    else:
        return type

def get_pois(types, radius, colors):
    res = {"type": "FeatureCollection", "features": []}
    for type in types:
        color = colors[type]
        ls = list(get_database_session().query('SELECT * FROM "points_of_interest" WHERE ("location"::tag =~ /^' + st.session_state.current_location + '$/' + (' AND "radius"::tag = \''+str(radius)+'\'' if radius else '')+' AND "poi_type"::tag = \''+type+'\')').get_points())
        res['features'] = res['features'] + [{"type": "Feature", "properties": {"v": 1, "color": color, "fill_color": color + [70]}, "geometry": json.loads(x["geojson"]), "id": type+str(i), "v": type_to_label(type)} for i,x in enumerate(ls)]
    return res        

def get_alerts():
    res = {"type": "FeatureCollection", "features": []}
    ls = list(get_database_session().query('SELECT "lat", "long",  "location", "score", "camera"  FROM "alerts"').get_points())
    res['features'] = [{"type": "Feature", "properties": {"v": x["location"].replace("_", " "), "color": [255,0,0], "fill_color": [255,0,0,70]}, "geometry": {"type": "Point", "coordinates": [x["long"], x["lat"]]}, "id": "alert"+str(i), "type": "alert"} for i,x in enumerate(ls)]    
    return res

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

def buffer_generation(gdf_POI, uniqueID, BUFFER_METERS):

    # select one node from gdf
    selected_node = gdf_POI[gdf_POI['POI_uniqueID'] == uniqueID].geometry
    lon = selected_node.x
    utm_zone = int((lon + 180) / 6) + 1
    epsg_utm = 32600 + utm_zone  # EPSG code for UTM (northern hemisphere)

    # convert to UTM for accurate buffering
    gdf_POI_utm = gdf_POI.to_crs(epsg=epsg_utm)
    selected_node_utm = gdf_POI_utm[gdf_POI_utm['POI_uniqueID'] == uniqueID].geometry

    buffer = selected_node_utm.buffer(BUFFER_METERS)

    boundary_utm = gpd.GeoSeries(buffer).unary_union
    gdf_boundary_utm = gpd.GeoDataFrame(geometry=[boundary_utm], crs=f"EPSG:{epsg_utm}")
    gdf_boundary = gdf_boundary_utm.to_crs(epsg=4326)
    boundary_geom = gdf_boundary.geometry.iloc[0]

    return boundary_geom, gdf_boundary

def create_clustered_map(POI, CITY, RESPONDER_TYPE, BUFFER_METERS):
    path = os.getenv('DATA_PATH', "../data")
    CITY = CITY.lower()
    # gdf POI with ID to identify files
    gdf_POI = gpd.read_file(f"{path}/{CITY}-locations-uniqueID.geojson", driver='GeoJSON')

    # association between ID and POI name
    dict_POI = gdf_POI.set_index('name')['POI_uniqueID'].to_dict()
    uniqueID = dict_POI[POI]

    # poi
    gdf_POI_attacked = gdf_POI[gdf_POI['name'] == POI]
    gdf_POI_attacked.set_crs(epsg=4326, inplace=True)

    # load specific impact file
    merged_gdf = gpd.read_file(f"{path}/processed/{CITY}/impacts_POI_{RESPONDER_TYPE}/{CITY}_impacts_POI_{uniqueID}_buffer_{BUFFER_METERS}.geojson")
    merged_gdf = merged_gdf.reset_index()

    # generate buffer boundary
    boundary_geom, gdf_boundary = buffer_generation(gdf_POI, uniqueID, BUFFER_METERS)

    # filter detached areas
    merged_gdf_detached = merged_gdf[merged_gdf['IMPACT'].isna()]
    merged_gdf['PERC'] = merged_gdf.apply(lambda row: (row['IMPACT']-1.0)*100, axis = 1)

    responder_names = {'hospital':'hospitals','police':'police stations','fire_station':'fire stations'}
    color_map = {'hospital':'Reds','police':'Blues','fire_station':'Oranges'}

    # get POI center
    poi_point = gdf_POI_attacked.geometry.iloc[0]
    center_lat, center_lon = poi_point.y, poi_point.x

    # convert merged_gdf to GeoJSON format
    merged_gdf_json = json.loads(merged_gdf.to_json())

    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles='openstreetmap')

    # add buffer boundary
    for _, boundary in gdf_boundary.iterrows():
        if boundary.geometry.geom_type == "Polygon":
            coords = list(boundary.geometry.exterior.coords)
            folium.Polygon(locations=[(lat, lon) for lon, lat in coords], color="red", weight=3, fill=False).add_to(m)

    # poi
    folium.Marker(
        location=[center_lat, center_lon],
        popup=f"POI: {POI}",
        icon=folium.Icon(color="red")
    ).add_to(m)

    # delay layer
    folium.Choropleth(
        geo_data=merged_gdf_json,
        name="Impact Zone",
        data=merged_gdf,
        columns=["index", "PERC"],
        key_on="feature.id",
        fill_color=color_map[RESPONDER_TYPE],
        fill_opacity=0.75,
        line_opacity=0.1,
        #legend_name=f"Delay Index in Accessibility to {responder_names[RESPONDER_TYPE]}",
        legend_name=f"[%] Increase in travel time to {responder_names[RESPONDER_TYPE]}",
        highlight = True
    ).add_to(m)

    # add Detached Areas if they exist
    if len(merged_gdf_detached) > 0:
        merged_gdf_detached = merged_gdf_detached.reset_index()
        merged_gdf_detached_json = json.loads(merged_gdf_detached.to_json())

        folium.GeoJson(
            merged_gdf_detached_json,
            name="Detached Areas",
            style_function=lambda feature: {
                "fillColor": "gray",
                "color": "gray",
                "weight": 1,
                "fillOpacity": 0.25,
            },
            tooltip=folium.GeoJsonTooltip(fields=["index"], aliases=["Detached Area Index"])
        ).add_to(m)


    # info_box_html = f'''
    # <div style="position: fixed; bottom: 150px; left: 50px; width: 250px; background-color: white; z-index:9999; padding: 12px; 
    #             font-size:14px; border-radius: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3); text-align: justify;">
    #     <b>Urban Resiliency</b><br>
    #     Accessibility delays to emergency responders after roads around a Point of Interest are blocked. 
    #     Areas highlighted indicate increased travel times to <b>{responder_names[RESPONDER_TYPE]}</b> due to the road network disruption.<br>
    #     - POI selected: <b>{POI}</b><br>
    # </div>
    # '''

    # legend_html = f'''
    # <div style="position: fixed; bottom: 50px; left: 50px; width: 220px; background-color: white; z-index:9999; padding: 10px; font-size:14px; border-radius: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
    #     <b>Legend</b><br>
    #     <i style="background: red; width: 12px; height: 2px; display: inline-block; margin-right: 8px;"></i> No-Access Area (Radius of <b>{BUFFER_METERS} m</b>)<br>
    # '''

    # if len(merged_gdf_detached) > 0:
    #     legend_html += '''<i style="background: gray; width: 12px; height: 12px; float: left; margin-right: 8px;"></i> Detached zone after disruption<br>'''

    # legend_html += '</div>'

    # m.get_root().html.add_child(folium.Element(info_box_html))

    # m.get_root().html.add_child(folium.Element(legend_html))

    # m.get_root().html.add_child(folium.Element("""
    #     <style>
    #         .leaflet-control.legend {
    #             font-size: 16px !important;  /* Adjust size */
    #             font-weight: bold;           /* Optional: Make it bold */
    #         }
    #     </style>
    # """))

    return m


def create_map(CITY, RESPONDER_TYPE):

    path = os.getenv('DATA_PATH', "../data")
    # Load GeoJSON file
    geojson_data = f"{path}/{CITY}_districts_{RESPONDER_TYPE}.geojson"
    with open(geojson_data, 'r') as f:
        geojson = json.load(f)

    # Load GeoDataFrame
    gdf = gpd.read_file(geojson_data)

    color_scale_oranges = [
        [0, "rgba(255, 255, 255, 0.3)"],  
        [0.25, "rgba(255, 204, 153, 0.45)"],
        [0.5, "rgba(255, 140, 0, 0.6)"], 
        [0.75, "rgba(255, 102, 0, 0.75)"], 
        [1, "rgba(204, 51, 0, 0.7)"]
    ]

    # Define a red color scale with transparency
    color_scale_reds = [
        [0, "rgba(255, 255, 255, 0.3)"], 
        [0.25, "rgba(255, 204, 204, 0.45)"],
        [0.5, "rgba(255, 102, 102, 0.6)"],
        [0.75, "rgba(204, 0, 0, 0.75)"], 
        [1, "rgba(153, 0, 0, 0.7)"] 
    ]

    if  RESPONDER_TYPE == 'police':
        color_scale_selected = color_scale_reds
    else:
        color_scale_selected = color_scale_oranges

    # Plot the choropleth map
    fig = px.choropleth_mapbox(
        gdf,                                   # The original GeoDataFrame
        geojson=geojson,                       # GeoJSON data
        locations='DISTRICT_CODE',             # Column linking to GeoJSON properties
        color='RNVI',              # Column for coloring
        featureidkey="properties.DISTRICT_CODE",  # GeoJSON property to match locations
        mapbox_style="carto-positron",         # Base map style
        center={"lat": 48.2082, "lon": 16.3738},  # Center on city
        zoom=10,                               # Zoom level
        color_continuous_scale=color_scale_selected,  # Custom red color scale
        title=f"District RNVI in {CITY}",        # Title of the map
        hover_name="DISTRICT_CODE",            # Show district code on hover
        hover_data=["RNVI","District Name","Population"],       # Show self_impact_mean on hover
    )

    # Customize the layout of the map for better aesthetics
    fig.update_layout(
        margin={"r":0,"t":50,"l":0,"b":0},  # Reduce margins for a more compact view
        title_text=f"District RNVI (Road Network Vulnerability Index) - {RESPONDER_TYPE}",  # Title text
        title_x=0.1,                         # Center the title
        title_font_size=24,                  # Increase title font size
        mapbox_style="carto-positron",       # Set mapbox style
        geo=dict(
            bgcolor="rgba(0,0,0,0)",         # Remove background color
            lakecolor="rgb(255, 255, 255)",  # Set water background to white
        ),
        font=dict(
            size=14,  # Set default font size
            color="black",  # Set font color to black
        ),
        showlegend=False,  # Hide the legend for a cleaner look
    )

    fig.add_annotation(
        text="District-based RNVI (Road Network Vulnerability Index):<br>"
            f"RNVI estimates the average factor by which travel times for closest {RESPONDER_TYPE} responders are increased<br>"
            "when accessing an area within the district after a random attack disrupts the road network.<br>"

            #For example, an index value of 1.20 indicates that travel times are 20% longer for first responders to reach their destination following the disruption."
            # "Each district is shaded based on its RNVI value. Hover over a district to see more details."
            ,
        xref="paper", yref="paper",       # Use relative coordinates
        x=0.5, y=-0.1,                    # Position it below the map
        showarrow=False,                  # No arrow pointing to the map
        font=dict(size=14, color="black"), # Set font size and color
        align="center",                   # Center-align the text
        bordercolor="black",              # Add border color for better visibility
        borderwidth=2,                    # Set border width
        borderpad=4,                      # Set padding around the text
        bgcolor="rgba(255, 255, 255, 0.8)" # Background for better readability
    )

    # Adjust the layout to ensure there's enough space for annotation
    fig.update_layout(
        margin={"r":0, "t":50, "l":0, "b":100},  # Increase bottom margin to make room for the annotation
        height=700
    )
    return fig

# PAGE

# asyncio.run(init())
style = '''
<style>
div[data-testid="stMainBlockContainer"] {padding: 3rem 5rem 5rem 5rem !important;}
div[data-testid="stExpander"] summary div[data-testid="stMarkdownContainer"] p {font-size: 1.2rem; font-weight: 600 !important;}
span[aria-label="Pedestrian, close by backspace"] {background-color: rgb(0, 104, 201)}
span[aria-label="Vehicle, close by backspace"] {background-color: rgb(255, 43, 43)}
span[aria-label="Bike, close by backspace"] {background-color: rgb(21, 130, 55)}
span[aria-label="Hospitals, close by backspace"] {background-color: rgb(255, 43, 43)}
span[aria-label="Police, close by backspace"] {background-color: rgb(0, 104, 201)}
span[aria-label="Fire station, close by backspace"] {background-color: rgb(217, 90, 0)}
</style>
'''
st.markdown(style, unsafe_allow_html=True)


st.header('Urban Layer: ' + st.session_state.current_location.replace("_", " "))
# st.write(
#     """
# The urban layer offers a set of intuitive and accessible
# tools designed to describe the ecological context surrounding a specific location. It includes
# four interrelated analytical components, each of which can be customized by selecting
# different radii -- 500 meters, 800 meters, 1,400 meters, or 4,000 meters -- allowing users to
# explore the area at varying levels of granularity, from micro to macro scale.
#     """
# )
st.write(
    """
The urban layer offers a set of intuitive and accessible
tools designed to describe the ecological context surrounding a specific location. It includes
four interrelated analytical components allowing users to
explore the area at varying levels of granularity, from micro to macro scale.
    """
)

# c1, c2 = st.columns(2)

# with c1:
#     st.subheader("Points of Interest")
#     st.write(
#         """
#         This map visualizes the distribution of buildings within the selected radius around a chosen point, helping to understand the built density of the area. Points of interest, among others, include commercial activities, schools, cultural and political institutions and the location of leisure activities.
#         """)


# with c2:
#     radius = st.selectbox('Radius', [500, 800, 1000, 4000])
#     zoom = 14 if radius == 500 else 13 if radius == 800 else 12 if radius == 1000 else 10


st.subheader("Points of Interest")
st.write(
    """
    This map visualizes the distribution of buildings within the selected radius around a chosen point, helping to understand the built density of the area. Points of interest, among others, include commercial activities, schools, cultural and political institutions and the location of leisure activities.
    """)


radius = 800
zoom = 13

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
    pickable=True,
    wireframe=False,
    get_fill_color="properties.fill_color",
    get_line_color="properties.color",
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


with st.expander("Street Network", expanded=True):
    sn1, sn2 = st.columns(2)
    with sn1:
        st.write("""
                The maps below visualize three types of street networks within the selected radius for the chosen location. The specific types are: 
                - Pedestrian routes (in :blue[blue]): paths accessible only by foot,
                - Vehicle routes (in :red[red]): roads open to motorized vehicles,
                - Bike routes (in :green[green]): lanes designated for bicycles.
                """)
    with sn2:
        selected_tags = st.multiselect("Network type", ["Pedestrian", "Vehicle", "Bike"], ["Pedestrian", "Vehicle", "Bike"])
        street_tags = [x.lower() + "_streets" for x in selected_tags]

    colors = {"pedestrian_streets": [40, 93, 208], "vehicle_streets": [213, 24, 52], "bike_streets": [23, 101, 13]}
    pois = get_pois(street_tags, radius, colors)

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


with st.expander("Services", expanded=True):
    ss1, ss2 = st.columns(2)
    with ss1:
        st.write("""
                The maps below focuses on the geospatial distribution of three critical emergency services within the selected radius:
                - Hospitals (:red[red]),
                - Police stations (:blue[blue]),
                - Fire stations (:orange[orange]).
                """)
    with ss2:
        selected_services = st.multiselect("Services", ["Hospitals", "Police", "Fire station"], ["Hospitals", "Police", "Fire station"])
        service_tags = [x.lower().replace(" ", "_") for x in selected_services]

    colors = {"police": [40, 93, 208], "hospitals": [213, 24, 52], "fire_station": [221, 117, 47]}
    ext_colors = {"Police Station": [40, 93, 208], "Hospital": [213, 24, 52], "Fire Station": [221, 117, 47]}
    pois = get_pois(service_tags, None, colors)

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
        The maps below calculates the shortest paths from the selected location to the nearest :red[hospital], :blue[police station], and :orange[fire station]. 
        Users can either input a specific address or select a public space under study. The platform will then compute and display the optimal routes to each service, 
        enabling users to assess the accessibility of the location in case of an emergency.
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
                    get_line_color=ext_colors[k],
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

city = st.session_state.current_city

if city == 'Vienna': city = "Wien"

location = st.session_state.current_location

st.header("Urban Resiliency")

legend_area = st.empty()

col1, col2 = st.columns(2)

with col1:
    st.write("""
            First responders/services: The types of first responders to which the shortest route is
            computed are:
        - Hospitals (:red[red]),
        - Police stations (:blue[blue]),
        - Fire stations (:orange[orange]).
             """)

with col2:
    st.write("""
            Area disruption around a selected location: Two radii options are given for the dimension of
        the interdicted area:
        - 600 meters
        - 1200 meters   
             """)
             
col1, col2 = st.columns(2)
with col1:
    responder = st.selectbox(
        "Service type",
        ("Hospital", "Fire station", "Police"),
    )

with col2:
    radius = st.selectbox("No access area radius", (600, 1200))

legend_area.markdown(f"""
        The urban resiliency submodule exploits the systemic modeling of network science to
        highlight the resilience of urban areas to disruptions in the road network. Specifically, the
        disruptions are simulated as interdiction of roads around selected locations. This disruption
        forces a re-routing of the shortest route of the nearby urban areas to selected types of first
        responders. This re-routing introduces a time delay in the emergency response and
        Resilience is evaluated by computing the additional percentage of travel time required by the
        first responders to reach the area.
                     
        Data for the reconstruction of the urban spatial features and road networks are obtained from
        OpenStreetMap. The urban space is discretized in H3 tiles and the travel time delay is
        computed for each tile after a disruption event is simulated in a selected location.          
        """)

        # Accessibility delays to emergency responders after roads around a Point of Interest are blocked. 
        # Areas highlighted indicate increased travel times to **{responder}** due to the road network disruption.

        # - POI Selected: **{location.replace("_", " ")}**
        # - No access area (red circle): radius of **{radius}** meters

st_folium(create_clustered_map(location, city, responder.lower().replace(" ", "_"), radius), use_container_width=True)

# st.plotly_chart(create_map(city, "hospitals"), use_container_width=True)

# st.plotly_chart(create_map(city, "police"), use_container_width=True)

