#!/usr/bin/env python

"""Serve the app's views on a webserver."""

# For webserver
from BaseHTTPServer import (BaseHTTPRequestHandler,
                            HTTPServer)
import cgi  # Common Gateway Interface

# For CRUD
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import (Base,
                    User,
                    Gift,
                    Claim,
                    Category)

from flask import (Flask,
                   request,
                   redirect,
                   url_for,
                   render_template,
                   flash,
                   jsonify,
                   g,
                   session,
                   make_response,
                   abort,
                   Blueprint)

# For OAuth
from oauth2client.client import (flow_from_clientsecrets,
                                 FlowExchangeError)
import random
import string
import json
import requests
import httplib2

import logging

# For making decorators
from functools import wraps

# Bind database
engine = create_engine('sqlite:///giftr.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
c = DBSession()


# Bind Flask
app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('flask.cfg')

# BLUEPRINTS
from views.client.gifts.views import gifts_blueprint
from views.client.claims.views import claims_blueprint
from views.client.categories.views import categories_blueprint

from views.auth.login.views import login_blueprint
from views.auth.logout.views import logout_blueprint

from views.api.gifts.views import api_gifts_blueprint
from views.api.categories.views import api_categories_blueprint

# register the blueprints
app.register_blueprint(gifts_blueprint)
app.register_blueprint(claims_blueprint)
app.register_blueprint(categories_blueprint)

app.register_blueprint(login_blueprint)
app.register_blueprint(logout_blueprint)

app.register_blueprint(api_gifts_blueprint)
app.register_blueprint(api_categories_blueprint)


# API Secrets and IDs
def get_google_client_id(json_file_name):
    """Get client id for Google OAuth2, from provided json file."""
    google_client_secrets_f = open(json_file_name, 'r')
    google_client_secrets = google_client_secrets_f.read()
    google_client_secrets_json = json.loads(google_client_secrets)
    return google_client_secrets_json['web']['client_id']


CLIENT_ID = get_google_client_id('google_client_secrets.json')


# DECORATORS


# CSRF protection
# Source: http://flask.pocoo.org/snippets/3/
@app.before_request
def csrf_protect():
    """Check on every POST form submit for a hidden CSRF PROTECT token."""
    if request.method == "POST" and request.form:
        token = session.pop('_csrf_token', None)
        if not token or token != request.form.get('_csrf_token'):
            log = 'CSRF Protection blocked a POST request.'
            log += '\nRequest was: ' + str(dict(request.form))
            log += '\nResponded with error 403.'
            logging.warning(log)
            abort(403)


def generate_csrf_token():
    """Return and store in session a random CSRF PROTECT token."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = get_random_string()
    return session['_csrf_token']


app.jinja_env.globals['csrf_token'] = generate_csrf_token


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.debug = True
    app.run(port=8080)