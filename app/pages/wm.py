import streamlit as st
from influxdb import InfluxDBClient
import plotly.graph_objects as go

import pandas as pd
import streamlit.components.v1 as components
import os

@st.cache_resource
def get_database_session():
    client = InfluxDBClient(host=os.environ['INFLUXDB_HOST'], port=os.environ['INFLUXDB_PORT'], database=os.environ['INFLUXDB_DATABASE'])
    return client


def get_alerts_as_df():
    ls = list(get_database_session().query('SELECT "lat", "long",  "location", "score", "camera"  FROM "alerts"').get_points())
    alert_df = pd.DataFrame.from_records([x for x in ls ])
    alert_df = alert_df[["lat", "long", "location", "score", "camera"]].drop_duplicates().groupby(["lat", "long", "location", "camera"]).mean().reset_index()
    
    return alert_df

alert_df = get_alerts_as_df()
center_lat = alert_df["lat"].mean(axis=0)
center_lon = alert_df["long"].mean(axis=0)

c1, c2 = st.columns([3,2])

with c1:
    fig = go.Figure()
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


    #st.map(st.session_state.locations, latitude="lat", longitude="long", zoom=10)

    st.plotly_chart(fig, use_container_width=True)    

with c2:
    components.iframe("https://precrisis.smartcommunitylab.it/streamlit/?embed=true", height=700)
    # st.html('<iframe src="https://precrisis.smartcommunitylab.it/streamlit/" width="100%" height="700" style="border:none;" />')