import streamlit as st  
import base64
from influxdb import InfluxDBClient
import plotly.express as px
import pandas as pd
import json
import plotly.graph_objects as go
import os 
from datetime import datetime, timedelta


@st.cache_resource
def get_database_session():
    client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST', "localhost"), port=os.getenv('INFLUXDB_PORT', 8086), database=os.getenv('INFLUXDB_DATABASE', 'precrisis'))
    return client

SERVER_URL = os.environ['SERVER_URL'] if 'SERVER_URL' in os.environ else '.'

TIMINGMAP = {
    "Vienna": {
        "video_anomaly_score": 0.04,
        "crowd_violence": 5/8,
        "panic_module": 0.08,
        "object_tracker": 0.04,
    },
    "Sofia": {
        "video_anomaly_score": 0.04,
        "crowd_violence": 5/8,
        "panic_module": 0.08,
        "object_tracker": 0.24,
    }
}

def get_cameras():
    ls = list(get_database_session().query('select camera, max(score) as score from video_anomaly_score where  "location"::tag =~ /^' + st.session_state.current_location + '$/ and camera !~/^cam.*/ and camera !~/.*20240529.*/ group by camera').get_points())
    return ls

# def get_camera_anomaly(camera):
    # alerts = list(client.query('select * from video_anomaly_score where "score"::field > 0.6;').get_points())


def get_interval(camera):
    ls = list(get_database_session().query('SELECT score, time FROM "video_anomaly_score" WHERE ("location"::tag =~ /^' + st.session_state.current_location + '$/) order by time ').get_points())
    return ls[0]["time"], ls[-1]["time"]


def get_camera_details(camera):
    ls = list(get_database_session().query('SELECT "image" FROM "thumbnails_busca_full" WHERE ("camera"::field =~ /^' + camera + '$/) or ("camera"::field=~/^cam01001mp4.mp4$/)').get_points())
    return ls[0] if len(ls) > 0 else []

def get_pois():
    type = "buildings"
    ls1 = list(get_database_session().query('SELECT * FROM "points_of_interest" WHERE ("location"::tag =~ /^' + st.session_state.current_location + '$/ AND "radius"::tag = \'500\' AND "poi_type"::tag = \''+type+'\')').get_points())
    type = "pois_gdf"
    ls2 = list(get_database_session().query('SELECT * FROM "points_of_interest" WHERE ("location"::tag =~ /^' + st.session_state.current_location + '$/ AND "radius"::tag = \'500\' AND "poi_type"::tag = \''+type+'\')').get_points())
    return {"type": "FeatureCollection", "features": 
            [{"type": "Feature", "properties": {"v": 1}, "geometry": json.loads(x["geojson"]), "id": str(i), "v": "buildings"} for i,x in enumerate(ls1)]
            + [{"type": "Feature", "properties": {"v": 1}, "geometry": json.loads(x["geojson"]), "id": str(i), "v": "pois_gdf"} for i,x in enumerate(ls2)]}

def get_poi_df(pois):
    df = pd.DataFrame.from_records(pois)
    return df[["id", "v"]]


def adjust_timeseries(res, interval, has_frame=True):
    if len(res) == 0:
        return res
    start_time = datetime.strptime(res[0]["time"], "%Y-%m-%dT%H:%M:%SZ")
    start_date = start_time.date()
    start_date = datetime(start_date.year, start_date.month, start_date.day)
    start_timestamp = datetime.timestamp(start_date)
    prev_ts = None
    prev_f = 0
    for i in range(len(res)):
        x = res[i]
        if has_frame: frame = int(x['frame'])
        else:
            if prev_ts == x['time']:
                frame = prev_f
            else:
                prev_ts = x['time']
                prev_f = prev_f + 1 
                frame = prev_f
            # print(frame)

        x["time"] = datetime.fromtimestamp(start_timestamp + frame*interval) 
    return res


def video_anomaly(camera):
    ls = list(get_database_session().query('SELECT score, frame, time FROM "video_anomaly_score" WHERE ("camera"::tag =~ /^' + camera + '$/) '))
    res = ls[0] if len(ls) > 0 else []
    return adjust_timeseries(res, TIMINGMAP[st.session_state.current_city]['video_anomaly_score'], True)

def violence(camera, fr = None, to = None):
    ls = list(get_database_session().query('SELECT prob, time FROM "crowd_violence" WHERE ("camera"::tag =~ /^' + camera + '$/) and time  <= \'' + to + '\' and time >= \'' + fr+'\''))
    res = ls[0] if len(ls) > 0 else []
    return adjust_timeseries(res, TIMINGMAP[st.session_state.current_city]['crowd_violence'], False)

def panic(camera, fr = None, to = None):
    ls = list(get_database_session().query('SELECT score, time FROM "panic_module" WHERE ("camera"::tag =~ /^' + camera + '$/) and time  <= \'' + to + '\' and time >= \'' + fr+'\''))
    res = ls[0] if len(ls) > 0 else []
    return adjust_timeseries(res, TIMINGMAP[st.session_state.current_city]['panic_module'], False)

def pedestrian_num(camera, fr = None, to = None):
    query = 'SELECT number_objects, time FROM "object_tracker" WHERE ("camera"::tag =~ /^' + camera + '$/) and time  <= \'' + to + '\' and time >= \'' + fr+'\' order by time' 
    ls = list(get_database_session().query(query))
    res = ls[0] if len(ls) > 0 else []
    # print(len(res))

    return adjust_timeseries(res, TIMINGMAP[st.session_state.current_city]['object_tracker'], False)


def pedestrian(camera, fr = None, to = None):
    ls = list(get_database_session().query('SELECT "avg_age", "min_age", "high_age", "avg_speed", "highest_speed", time FROM "object_tracker" WHERE ("camera"::tag =~ /^' + camera + '$/) and time  <= \'' + to + '\' and time >= \'' + fr+'\''))
    res = ls[0] if len(ls) > 0 else []
    return adjust_timeseries(res, TIMINGMAP[st.session_state.current_city]['object_tracker'], False)

def get_video():
    ls = list(get_database_session().query(f'select DISTINCT inspect from video_busca WHERE ("camera"::tag =~ /^{st.session_state.current_camera}$/);').get_points())
    return ls[0]["distinct"] if len(ls) > 0 else None

def get_anomaly_video():
    ls = list(get_database_session().query(f'select DISTINCT inspect from video_anomaly_score WHERE ("camera"::tag =~ /^{st.session_state.current_camera}$/);').get_points())
    link = ls[0]["distinct"] if len(ls) > 0 else None
    if link:
        link = link.replace("mp4.mp4", "mp4")
    return link

def get_clips():
    ls = list(get_database_session().query(f'SELECT "clip_name" FROM "panic_module_clips" WHERE ("camera"::tag =~ /^{st.session_state.current_camera}$/);').get_points())
    return ls

def get_dataframe(date):
    cameras = get_cameras()

    start_time = datetime.strptime(date, "%Y-%m-%d")
    end_time = start_time + timedelta(days=1)

    # Generate half-hour intervals
    intervals = []
    current_time = start_time
    while current_time < end_time:
        t = current_time.strftime("%H:%M")
        intervals.append(t)
        current_time += timedelta(minutes=30)

    # Create the DataFrame
    df = pd.DataFrame(cameras, columns=["camera"])
    for interval in intervals:
        df[interval] = -1.0  # Initialize columns with None or any default value

    df.set_index("camera", inplace=True)
    # ls = list(get_database_session().query(f'select "max", camera,location, time from( select max(score),camera,location from video_anomaly_score where ("location"::tag =~ /^{st.session_state.current_location}$/ ' + ') group by time(30m)) where'  + ' time >= ' + date + ' and time < ' + '\'' + end_time.isoformat(sep=" ") + '\'').get_points())
    video_ls = list(get_database_session().query(f'select camera from video_busca where ("location"::tag =~ /^{st.session_state.current_location}$/ ' + ') and '  + ' time >= ' + date + ' and time < ' + '\'' + end_time.isoformat(sep=" ") + '\'').get_points())
    ls = list(get_database_session().query(f'select "max", camera,location, time from( select max(score),camera,location from video_anomaly_score where ("location"::tag =~ /^{st.session_state.current_location}$/ ' + ') group by time(30m)) where'  + ' time >= ' + date + ' and time < ' + '\'' + end_time.isoformat(sep=" ") + '\'').get_points())
    scores = {} 
    for x in ls:
        time = datetime.strptime(x["time"], "%Y-%m-%dT%H:%M:%SZ").strftime("%H:%M")
        scores[time] = x["max"]
    for x in video_ls:
        time = datetime.strptime(x["time"], "%Y-%m-%dT%H:%M:%SZ").strftime("%H:%M")
        if x["camera"] in df.index:
            # round time to nearest 30 minutes
            time = time[:-2] + "00"
            if time in df.columns:
                df.at[x["camera"], time] = 0 if scores.get(time) is None else (scores[time] or 0)

    def hl(v, props=''):
        return 'background-color:#e6ffe6;' if v >= 0 and v <= 0.6 else 'background-color:#ffe6e6;' if v> 0.6 else ''
    return df.style.format(lambda v: ' ').map(hl, props='')

def get_camera_name(camera):
    c = camera["camera"]
    s = c
    if 'Sofia' == st.session_state.current_city:
        c = c.replace("poligon2", "").replace("ipcamera", "")
        s = 'Cam' + c[0] + '-' + datetime.strptime(c[1:13], "%Y%m%d%H%M").strftime("%d-%m-%Y %H:%M")
    elif 'Vienna' == st.session_state.current_city:
        s = 'Cam' + c[0] + '-' + datetime.strptime(c[1:13], "%Y%m%d%H%M").strftime("%d-%m-%Y %H:%M")

    if camera["score"] > 0.6:
        s = s + ' (anomaly detected)'
    return s

# PAGE (VIDEO)
style = '''
<style>
div[data-testid="stMainBlockContainer"] {padding: 3rem 5rem 5rem 5rem !important;}
</style>
'''
st.markdown(style, unsafe_allow_html=True)

st.header("Human Dynamics Layer: " +st.session_state.current_location.replace("_", " "))

# pois = get_pois()
# df = get_poi_df(pois["features"])


cam1, cam2, cam3 = st.columns([1,1,1], vertical_alignment="bottom")
with cam1:
    cameras = get_cameras()
    cameras.sort(key=lambda x: x["camera"])

    curr_camera = None
    if len(cameras) > 0:
        curr_camera = st.selectbox("Camera", [x for x in cameras], format_func=get_camera_name)["camera"]
        st.session_state.current_camera = curr_camera
    else:
        st.write("No camera data available")

    # if curr_camera:
    #     # camera_container.write("Camera sample")
    #     # st.image(base64.decodebytes(bytes(get_camera_details(curr_camera)["image"], "utf-8")))
    #     try:
    #         st.image(f"{SERVER_URL}/videos/{curr_camera}.jpg", use_container_width=True)
    #     except Exception as e: 
    #         print(e)
    #         st.image(f"./assets/placeholder.jpg", use_container_width=True)

if curr_camera:
    with cam2:
        __from, __to = get_interval(curr_camera)
        __from_date = __from.split("T")[0]
        # d = st.date_input("Date", datetime.strptime(__from_date, "%Y-%m-%d"))


    with cam3:
        with_tracking = st.toggle("Anomaly Detection", value=False)

    vadf = pd.DataFrame.from_records(video_anomaly(curr_camera))
    vdf = pd.DataFrame.from_records(violence(curr_camera, __from, __to))
    pdf = pd.DataFrame.from_records(panic(curr_camera, __from, __to))

    ct1, ct2 = st.columns([2,1])
    with ct1:
        # st.caption("Video")
        video = get_anomaly_video() if with_tracking else get_video()
        if video:
            try:
                v1 = st.video(f"{SERVER_URL}/videos/{video}", autoplay=True, loop=True)
            except Exception as e: 
                print(e)
        
    with ct2:
        # with st.container(height=800, border=False):
            # VIDEO ANOMALY
            if vadf.size > 0:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=vadf["time"], y=vadf["score"]))
                fig.add_hline(y=0.6, line_width=3, line_dash="dash", line_color="red")
                fig.add_hline(y=0.4, line_width=2, line_dash="dash", line_color="orange")
                fig.update_layout( title=dict( text='Anomaly Detection' ), height=200, margin={"r":0,"t":30,"l":0,"b":0})
                with st.container(border=True):
                    st.plotly_chart(fig, use_container_width=True)

            # VIOLENCE
            if vdf.size > 0:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=vdf["time"], y=vdf["prob"]))
                fig.add_hline(y=0.8, line_width=3, line_dash="dash", line_color="red")
                fig.add_hline(y=0.4, line_width=2, line_dash="dash", line_color="orange")
                fig.update_layout( title=dict( text='Crowd Violence Activity Detection' ), height=200, margin={"r":0,"t":30,"l":0,"b":0})

                with st.container(border=True):
                    st.plotly_chart(fig, use_container_width=True)
            

    ct11, ct12, ct13 = st.columns([1, 1, 1])
    with ct11:
        # PEDESTRIAN NUM
        df = pd.DataFrame.from_records(pedestrian_num(curr_camera, __from, __to))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time"], y=df["number_objects"]))
        fig.update_layout( title=dict( text='Number of Pedestrians' ), height=200, margin={"r":0,"t":30,"l":0,"b":0})

        with st.container(border=True):
            st.plotly_chart(fig, use_container_width=True)
    with ct12:
        # PEDESTRIAN PERSISTENCE
        df = pd.DataFrame.from_records(pedestrian(curr_camera, __from, __to))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time"], y=df["avg_age"], name="Avg", marker_color="#709CEC"))
        fig.add_trace(go.Scatter(x=df["time"], y=df["min_age"], name="Min", marker_color="green"))
        fig.add_trace(go.Scatter(x=df["time"], y=df["high_age"], name="Max", marker_color="#9035C0"))
        fig.add_hline(y=200, line_width=1, line_color="red")
        fig.add_hline(y=100, line_width=1, line_color="orange")
        fig.add_hline(y=50, line_width=1, line_color="green")
        fig.update_layout( title=dict( text='Persistence of Pedestrians (Frames)' ), height=200, margin={"r":0,"t":30,"l":0,"b":0})

        with st.container(border=True):
            st.plotly_chart(fig, use_container_width=True)

    with ct13:
        # PANIC
        if pdf.size > 0:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=pdf["time"], y=pdf["score"]))
            fig.add_hline(y=0.8, line_width=3, line_dash="dash", line_color="red")
            fig.add_hline(y=0.4, line_width=2, line_dash="dash", line_color="orange")
            fig.update_layout( title=dict( text='Crowd Panic Activity Detection' ), height=200, margin={"r":0,"t":30,"l":0,"b":0})

            with st.container(border=True):
                st.plotly_chart(fig, use_container_width=True)


            # PEDESTRIAN SPEED
            # fig = go.Figure()
            # fig.add_trace(go.Scatter(x=df["time"], y=df["avg_speed"], name="Avg", marker_color="#EDD021"))
            # fig.add_trace(go.Scatter(x=df["time"], y=df["highest_speed"], name="Max", marker_color="#9035C0"))
            # fig.add_hline(y=0.04, line_width=1, line_color="red")
            # fig.add_hline(y=0.03, line_width=1, line_color="orange")
            # fig.add_hline(y=0.02, line_width=1, line_color="green")
            # fig.update_layout( title=dict( text='Pedestrian Speed' ), height=300, margin={"r":0,"t":30,"l":0,"b":0})

            # with st.container(border=True):
            #     st.plotly_chart(fig, use_container_width=True)
    # exp = st.expander("**Video Details...**")
    # with exp:

    #     clips = get_clips()
    #     ct1, ct2, ct3 = st.columns(3)
    #     with ct1:
    #         st.caption("Video")
    #     with ct2:
    #         st.caption("Anomaly Detection")
    #     with ct3:
    #         if len(clips) > 0:
    #             curr_clip = st.selectbox("Crowd Panic Clips", [x["clip_name"] for x in clips])
            

    #     c1, c2, c3 = st.columns(3, vertical_alignment="bottom")

    #     with c1:
    #         video = get_video()
    #         if video:
    #             try:
    #                 v1 = st.video(f"{SERVER_URL}/videos/{video}", autoplay=True, loop=True)
    #                 # v1 = st.components.v1.iframe(f"{SERVER_URL}/videos/{video}")
    #             except Exception as e: 
    #                 print(e)

    #     with c2:
    #         anomaly_video = get_anomaly_video()
    #         if anomaly_video:
    #             try:
    #                 v22 = st.video(f"{SERVER_URL}/videos/{anomaly_video}",  start_time=1, autoplay=True, loop=True)
    #             except Exception as e: 
    #                 print(e)
    #                 pass

    #     with c3:
    #         if len(clips) > 0:
    #             try:
    #                 v3 = st.video(f"{SERVER_URL}/videos/{curr_clip}", format="mp4", autoplay=True, loop=True, start_time=1)
    #             except Exception as e: 
    #                 print(e)
        
        # fig = go.Figure()
        # if vadf.size > 0:
        #     fig.add_trace(go.Scatter(x=vadf["time"], y=vadf["score"], name="Anomaly Score"))
        #     fig.add_trace(go.Scatter(x=vdf["time"], y=vdf["prob"], name="Crowd Violence"))
        #     fig.add_trace(go.Scatter(x=pdf["time"], y=pdf["score"], name="Crowd Panic"))
        #     fig.update_layout( title=dict( text='Behavior Analysis' ), height=300, margin={"r":0,"t":30,"l":0,"b":0})
        #     st.plotly_chart(fig, use_container_width=True)


# col2, col3 = st.columns([1,1])


# if curr_camera:
    # with col2:
    #     # VIDEO ANOMALY
    #     if vadf.size > 0:
    #         fig = go.Figure()
    #         fig.add_trace(go.Scatter(x=vadf["time"], y=vadf["score"]))
    #         fig.add_hline(y=0.6, line_width=3, line_dash="dash", line_color="red")
    #         fig.add_hline(y=0.4, line_width=2, line_dash="dash", line_color="orange")
    #         fig.update_layout( title=dict( text='Anomaly Detection' ), height=300, margin={"r":0,"t":30,"l":0,"b":0})
    #         with st.container(border=True):
    #             st.plotly_chart(fig, use_container_width=True)

    #     # VIOLENCE
    #     if vdf.size > 0:
    #         fig = go.Figure()
    #         fig.add_trace(go.Scatter(x=vdf["time"], y=vdf["prob"]))
    #         fig.add_hline(y=0.8, line_width=3, line_dash="dash", line_color="red")
    #         fig.add_hline(y=0.4, line_width=2, line_dash="dash", line_color="orange")
    #         fig.update_layout( title=dict( text='Crowd Violence Activity Detection' ), height=300, margin={"r":0,"t":30,"l":0,"b":0})

    #         with st.container(border=True):
    #             st.plotly_chart(fig, use_container_width=True)
        
    #     # PANIC
    #     if pdf.size > 0:
    #         fig = go.Figure()
    #         fig.add_trace(go.Scatter(x=pdf["time"], y=pdf["score"]))
    #         fig.add_hline(y=0.8, line_width=3, line_dash="dash", line_color="red")
    #         fig.add_hline(y=0.4, line_width=2, line_dash="dash", line_color="orange")
    #         fig.update_layout( title=dict( text='Crowd Panic Activity Detection' ), height=300, margin={"r":0,"t":30,"l":0,"b":0})

    #         with st.container(border=True):
    #             st.plotly_chart(fig, use_container_width=True)


    # with col3:
        # # PEDESTRIAN NUM
        # df = pd.DataFrame.from_records(pedestrian_num(curr_camera, __from, __to))
        # fig = go.Figure()
        # fig.add_trace(go.Scatter(x=df["time"], y=df["number_objects"]))
        # fig.update_layout( title=dict( text='Number of Pedestrians' ), height=300, margin={"r":0,"t":30,"l":0,"b":0})

        # with st.container(border=True):
        #     st.plotly_chart(fig, use_container_width=True)

        # # PEDESTRIAN PERSISTENCE
        # df = pd.DataFrame.from_records(pedestrian(curr_camera, __from, __to))
        # fig = go.Figure()
        # fig.add_trace(go.Scatter(x=df["time"], y=df["avg_age"], name="Avg", marker_color="#709CEC"))
        # fig.add_trace(go.Scatter(x=df["time"], y=df["min_age"], name="Min", marker_color="green"))
        # fig.add_trace(go.Scatter(x=df["time"], y=df["high_age"], name="Max", marker_color="#9035C0"))
        # fig.add_hline(y=200, line_width=1, line_color="red")
        # fig.add_hline(y=100, line_width=1, line_color="orange")
        # fig.add_hline(y=50, line_width=1, line_color="green")
        # fig.update_layout( title=dict( text='Persistence of Pedestrians (Frames)' ), height=300, margin={"r":0,"t":30,"l":0,"b":0})

        # with st.container(border=True):
        #     st.plotly_chart(fig, use_container_width=True)

        # # PEDESTRIAN SPEED
        # fig = go.Figure()
        # fig.add_trace(go.Scatter(x=df["time"], y=df["avg_speed"], name="Avg", marker_color="#EDD021"))
        # fig.add_trace(go.Scatter(x=df["time"], y=df["highest_speed"], name="Max", marker_color="#9035C0"))
        # fig.add_hline(y=0.04, line_width=1, line_color="red")
        # fig.add_hline(y=0.03, line_width=1, line_color="orange")
        # fig.add_hline(y=0.02, line_width=1, line_color="green")
        # fig.update_layout( title=dict( text='Pedestrian Speed' ), height=300, margin={"r":0,"t":30,"l":0,"b":0})

        # with st.container(border=True):
        #     st.plotly_chart(fig, use_container_width=True)