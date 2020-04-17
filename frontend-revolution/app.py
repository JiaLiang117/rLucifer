import os
import urllib
import datetime
import uuid
from chalice import Chalice, Response
import jinja2
import boto3
from botocore.vendored import requests

app = Chalice(app_name='frontend-revolution')

def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(loader=jinja2.FileSystemLoader(path)).get_template(filename).render(context)

@app.route("/")
def index():
    template = render("chalicelib/templates/index.html", {})
    return Response(template, status_code=200, headers={
        "Content-Type": "text/html",
        "Access-Control-Allow-Origin": "*"
    })


@app.route('/create_session', methods=['GET'])
def create_session():

    template = render("chalicelib/templates/create_session.html", {})
    return Response(template, status_code=200, headers={
        "Content-Type": "text/html",
        "Access-Control-Allow-Origin": "*"
    })








# apis
@app.route("/join_session", methods=["POST"], content_types=["application/x-www-form-urlencoded"])
def order_form():
    """to dump data from form """
    data = urllib.parse.parse_qs(app.current_request.__dict__.get("_body"))
    data = {key:value[0] for key, value in data.items()}

    return data

@app.route("/create_session", methods=["POST"], content_types=["application/x-www-form-urlencoded"])
def order_form():
    """to dump data from form """

    return "hello world"