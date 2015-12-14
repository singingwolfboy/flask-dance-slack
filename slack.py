import os
import sys
import logging
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.urls import url_encode, url_decode
import flask
from flask import Flask, redirect, url_for
from flask_dance.consumer import OAuth2ConsumerBlueprint
from raven.contrib.flask import Sentry
from requests.auth import AuthBase
from urlobject import URLObject

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
sentry = Sentry(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config["SLACK_OAUTH_CLIENT_ID"] = os.environ.get("SLACK_OAUTH_CLIENT_ID")
app.config["SLACK_OAUTH_CLIENT_SECRET"] = os.environ.get("SLACK_OAUTH_CLIENT_SECRET")


class SlackOAuth(AuthBase):
    """
    Slack wants the access token to be passed in a `token` GET parameter or POST
    parameter, rather than using the `Authorization: Bearer` header. This is
    annoying, but we can make it work using this custom Auth object.
    """
    def __init__(self, blueprint):
        self.blueprint = blueprint

    def __call__(self, r):
        if self.blueprint.token:
            access_token = self.blueprint.token.get("access_token")
        else:
            access_token = None
        if not access_token:
            return r

        if r.method == "GET":
            url = URLObject(r.url)
            if not "token" in url.query_dict:
                url = url.add_query_param("token", access_token)
            r.url = url
        elif r.method == "POST":
            args = url_decode(r.body)
            args.setdefault("token", access_token)
            r.body = url_encode(args)
        return r


slack_bp = OAuth2ConsumerBlueprint("slack", __name__,
    base_url="https://slack.com/api/",
    authorization_url="https://slack.com/oauth/authorize",
    token_url="https://slack.com/api/oauth.access",
    scope=["identify", "chat:write:bot"],
)
slack_bp.auth = SlackOAuth(slack_bp)
slack_bp.from_config["client_id"] = "SLACK_OAUTH_CLIENT_ID"
slack_bp.from_config["client_secret"] = "SLACK_OAUTH_CLIENT_SECRET"
app.register_blueprint(slack_bp, url_prefix="/login")


@app.route("/")
def index():
    slack = slack_bp.session
    if not slack.authorized:
        return redirect(url_for("slack.login"))
    resp = slack.post("chat.postMessage", data={
        "channel": "#general",
        "text": "ping",
        "icon_emoji": ":robot_face:",
    })
    assert resp.ok, resp.text
    return resp.text

if __name__ == "__main__":
    app.run()
