import plotly.express as px
import geopandas as gpd
import json

import streamlit as st
import os

import folium
from streamlit_folium import st_folium

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

city = st.session_state.current_city

if city == 'Vienna': city = "Wien"

location = st.session_state.current_location

st.header("Urban Resiliency")

legend_area = st.empty()

col1, col2 = st.columns(2)

with col1:
    responder = st.selectbox(
        "Service type",
        ("hospital", "fire_station", "police"),
    )

with col2:
    radius = st.selectbox("No access area radius", (600, 1200))

legend_area.markdown(f"""
        Accessibility delays to emergency responders after roads around a Point of Interest are blocked. 
        Areas highlighted indicate increased travel times to **{responder}** due to the road network disruption.

        - POI Selected: **{location}**
        - No access area (red circle): radius of **{radius}** meters
        """)

st_folium(create_clustered_map(location, city, responder, radius), use_container_width=True)

# st.plotly_chart(create_map(city, "hospitals"), use_container_width=True)

# st.plotly_chart(create_map(city, "police"), use_container_width=True)


