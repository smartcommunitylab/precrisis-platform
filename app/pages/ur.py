import plotly.express as px
import geopandas as gpd
import json

import streamlit as st
import os

def create_map(RESPONDER_TYPE):

    path = os.environ['DATA_PATH']
    # Load GeoJSON file
    geojson_data = f"{path}/vienna_districts_{RESPONDER_TYPE}.geojson"
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
        center={"lat": 48.2082, "lon": 16.3738},  # Center on Vienna
        zoom=10,                               # Zoom level
        color_continuous_scale=color_scale_selected,  # Custom red color scale
        title="District RNVI in Vienna",        # Title of the map
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


st.plotly_chart(create_map("hospitals"), use_container_width=True)

st.plotly_chart(create_map("police"), use_container_width=True)

