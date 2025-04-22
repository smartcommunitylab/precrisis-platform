import streamlit as st
import plotly.graph_objects as go

import pandas as pd
from influxdb import InfluxDBClient
import os

@st.cache_resource
def get_database_session():
    client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST', "localhost"), port=os.getenv('INFLUXDB_PORT', 8086), database=os.getenv('INFLUXDB_DATABASE', 'precrisis'))
    return client

def get_alerts_as_df():
    ls = list(get_database_session().query('SELECT "lat", "long",  "location", "score", "camera"  FROM "alerts"').get_points())
    alert_df = pd.DataFrame.from_records([x for x in ls ])
    alert_df = alert_df[["lat", "long", "location", "score", "camera"]].drop_duplicates().groupby(["lat", "long", "location", "camera"]).mean().reset_index()
    
    return alert_df


current_df = pd.DataFrame.from_records([x for x in st.session_state.locations if x['location'] == st.session_state.current_location])
df = pd.DataFrame.from_records(st.session_state.locations)
alert_df = get_alerts_as_df()

center_lat = df["lat"].mean(axis=0)
center_lon = df["long"].mean(axis=0)

st.title("PRECRISIS Platform")

fig = go.Figure()

fig.add_trace(go.Scattermap(
        lat=df.lat,
        lon=df.long,
        mode='markers',
        marker=go.scattermap.Marker(
            size=17,
            color='rgb(0, 0, 255)',
            opacity=0.3
        ),
        text=df.location,
        hoverinfo='text'
    ))

fig.add_trace(go.Scattermap(
        lat=current_df.lat,
        lon=current_df.long,
        mode='markers',
        marker=go.scattermap.Marker(
            size=25,
            color='rgb(255, 120, 10)',
            opacity=0.9
        ),
        text=current_df.location,
        hoverinfo='text'
    ))
fig.add_trace(go.Scattermap(
        lat=current_df.lat,
        lon=current_df.long,
        mode='markers',
        marker=go.scattermap.Marker(
            size=10,
            color='rgb(255, 255, 255)',
            opacity=0.9
        ),
        text=current_df.location,
        hoverinfo='text'
    ))

fig.add_trace(go.Scattermap(
        lat=alert_df.lat,
        lon=alert_df.long,
        mode='markers',
        marker=go.scattermap.Marker(
            size=17,
            color='rgb(255, 0, 0)',
            opacity=0.9
        ),
        text=alert_df.location,
        hoverinfo='text'
    ))
fig.update_layout(
    autosize=True,
    hovermode='closest',
    showlegend=False,
    map=dict(
        bearing=0,
        center=dict(
            lat=center_lat,
            lon=center_lon
        ),
        pitch=0,
        zoom=11,
        style='light'
    ),
    margin={"r":0,"t":0,"l":0,"b":0},
    height=800
)


st.plotly_chart(fig, use_container_width=True, selection_mode='points')