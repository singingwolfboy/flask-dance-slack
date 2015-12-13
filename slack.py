import os
import sys
import logging
from werkzeug.contrib.fixers import ProxyFix
import flask
from flask import Flask, redirect, url_for
from flask_dance.consumer import OAuth2ConsumerBlueprint
from raven.contrib.flask import Sentry

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
sentry = Sentry(app)
logging.setLevel(logging.INFO)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config["SLACK_OAUTH_CLIENT_ID"] = os.environ.get("SLACK_OAUTH_CLIENT_ID")
app.config["SLACK_OAUTH_CLIENT_SECRET"] = os.environ.get("SLACK_OAUTH_CLIENT_SECRET")
slack_bp = OAuth2ConsumerBlueprint("slack", __name__,
    base_url="https://slack.com/api/",
    authorization_url="https://slack.com/oauth/authorize",
    token_url="https://slack.com/api/oauth.access",
    scope=["identify", "chat:write:bot"],
)
slack_bp.from_config["client_id"] = "SLACK_OAUTH_CLIENT_ID"
slack_bp.from_config["client_secret"] = "SLACK_OAUTH_CLIENT_SECRET"
app.register_blueprint(slack_bp, url_prefix="/login")

slack = slack_bp.session


@app.route("/")
def index():
    logging.info("flask.session = %s", flask.session)
    logging.info("slack_bp.token = %s", slack_bp.token)
    logging.info("slack.token = %s", slack.token)
    logging.info("slack.authorized = %s", slack.authorized)
    if not slack.authorized:
        return redirect(url_for("slack.login"))
    resp = slack.post("chat.postMessage", data={
        "token": slack_bp.token,
        "channel": "#general",
        "text": "ping",
        "emoji_icon": ":frog:",
    })
    assert resp.ok, resp.text
    return "I said ping!"

if __name__ == "__main__":
    app.run()
