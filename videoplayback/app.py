#!/usr/bin/env python
import json
import os
from os import listdir
from os.path import isfile, join
from unicodedata import name

import flask_login
import requests
from flask import (
    Flask,
    Response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import LoginManager, UserMixin, login_user
from matplotlib import use
from oauthlib.oauth2 import WebApplicationClient

# configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = os.environ.get("GOOGLE_DISCOVERY_URL", None)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

VIDEO_FOLDER = "videos/"
EXTERNAL_URL = os.environ.get("EXTERNAL_URL", None)


# add classes
class User(UserMixin):
    def __init__(self, id, name, email):
        self.name = name
        self.id = id
        self.email = email
        self.oath_passed = False

        def is_active(self):
            # return self.active
            return True

        def is_anonymous(self):
            return False

        def is_authenticated(self):
            return self.oath_passed


original_url = ""

users = {}

# flask config
client = WebApplicationClient(GOOGLE_CLIENT_ID)
login_manager = LoginManager()
app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
login_manager.init_app(app)

# login routing


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


@login_manager.unauthorized_handler
def unauthorized():
    global original_url
    original_url = str(request.path)
    return redirect(EXTERNAL_URL + "/login")


@login_manager.user_loader
def load_user(user_id):
    if user_id not in users:
        return

    user = User(id=user_id, name="", email="")
    return user


@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=EXTERNAL_URL + "/login/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    # Find out what URL to hit to get tokens that allow you to ask for
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send request to get tokens
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=EXTERNAL_URL + "/login/callback",
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens
    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        # picture = userinfo_response.json()["picture"]
        try:
            users_name = userinfo_response.json()["given_name"]
        except Exception as e:
            users_name = "Blank"
    else:
        return "User email not available or not verified by Google.", 400

    user = User(id=unique_id, name=users_name, email=users_email)
    user.oath_passed = True

    # Begin user session by logging the user in
    flask_login.login_user(user)

    # add user
    global users
    users[user.id] = {"name": user.name, "email": user.email}

    # Send user back to homepage
    # return redirect(url_for("index"))
    global original_url
    url_redirec = original_url.split("/")
    go_bak = url_for("show_video", id=url_redirec[1], timestamp=url_redirec[2])
    return redirect(go_bak)
    # return "Logged"


def update_files():
    filenames = [f for f in listdir(VIDEO_FOLDER) if isfile(join(VIDEO_FOLDER, f))]
    return filenames


@app.route("/")
def home():
    return "Hello World"


@app.route("/videos/<path:path>")
# @flask_login.login_required
def send_video(path):
    return send_from_directory("videos", path)


@app.route("/twitter-explorer/<path:path>")
# @flask_login.login_required
def send_explorer(path):
    return send_from_directory("twitter-explorer", path)


@app.route("/grafana/<path:path>")
def send_images(path):
    return send_from_directory("images-grafana", path)


@app.route("/<id>/<timestamp>")
@flask_login.login_required
def show_video(id, timestamp):
    filenames = update_files()
    filenames = [name.split(".mp4")[0] for name in filenames]
    video_name = str(id)
    # timestamp = (int(float(timestamp)) * 60) + int(str(float(timestamp)).split('.')[1])
    timestamp = float(timestamp)
    print(filenames)

    # if video_name not in filenames:
    #     return Response("Not Found")

    output_file = video_name + "_original.mp4"
    anon_video = video_name + "_anomaly_score.mp4"
    obj_video = video_name + "_anomaly_pred_err.mp4"
    pred_err_video = video_name + "_anomaly_recon_err.mp4"

    return render_template(
        "video_player.html",
        raw_video=output_file,
        anon_video=anon_video,
        obj_video=obj_video,
        pred_err_video=pred_err_video,
        timestamp=timestamp,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
