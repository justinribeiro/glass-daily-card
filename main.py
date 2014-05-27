#!/usr/bin/python
#
#
# Copyright 2014 Justin Ribeiro. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Launch Glass Daily Card."""

__author__ = 'justin@justinribeiro.com (Justin Ribeiro)'

import json
import random
import string
import datetime
import httplib2

from flask import Flask
from flask import make_response
from flask import render_template
from flask import request
from flask import session

from apiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from oauth2client.appengine import StorageByKeyName
from oauth2client.appengine  import CredentialsModel

from simplekv.memory import DictStore
from flaskext.kvsession import KVSessionExtension

from google.appengine.ext import ndb
from models import CronCards, UserProperties

glassdailycard = Flask('glass-daily-card')
glassdailycard.secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits)
                                for x in xrange(32))

# Handles our sessions
store = DictStore()
KVSessionExtension(store, glassdailycard)

def _oauth_flow():
    """Prepare an OAuth flow."""
    required_scopes = ('https://www.googleapis.com/auth/glass.location', 
        'https://www.googleapis.com/auth/glass.timeline', 
        'https://www.googleapis.com/auth/plus.login')
    oauthflow = flow_from_clientsecrets('client_secrets.json', scope=required_scopes, redirect_uri='postmessage')
    oauthflow.params['access_type'] = 'offline'
    return oauthflow


def _authorized_http(credentials):
    """Create an authorized HTTP object with some credentials."""
    return(credentials.authorize(httplib2.Http()))


def _authorized_mirror_service(credentials):
    """Create a Mirror API service with some credentials."""
    return(build('mirror', 'v1', http=_authorized_http(credentials)))


def _credentials_for_user(userid):
    """Find the location of the user's credentials in NDB."""
    return(StorageByKeyName(CredentialsModel, userid, 'credentials'))

@glassdailycard.route('/')
def index():
    """Display the main page."""
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    session['state'] = state
    return(render_template('index.html', state=state))

@glassdailycard.route('/connect', methods=['POST'])
def connect():
    """Store the user's data and finish signing them in."""

    # Ensure that the request is not a forgery and that the user sending
    # this connect request is the expected user.
    if request.args.get('state') != session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Auth code to credentials object
    try:
        user_credentials = _oauth_flow().step2_exchange(request.data)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    user_id = user_credentials.id_token['sub']
    stored_credentials = session.get('credentials')
    stored_userid = session.get('user_id')

    if stored_credentials is not None and user_id == stored_userid:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    session['credentials'] = user_credentials
    session['user_id'] = user_id

    # Check the datastore for the user
    if _credentials_for_user(user_id).get() is None:
        # Store the user's credentials so you can use them even after this
        # step is done.
        _credentials_for_user(user_id).put(user_credentials)

        # Sample user properties that we might want to give a user
        # Example: do they want email, do they want cards on the weekends
        user_properties = UserProperties(id=session['user_id'], email=False, weekends=False)
        user_properties.put()

        # Create a an auth'ed Mirror API serivce
        mirror_service = _authorized_mirror_service(user_credentials)

        mirror_service.timeline().insert(body={
            'notification': {'level': 'DEFAULT'},
            'text': 'Welcome to Glass Daily Card!',
            'menuItems': [{'action': 'DELETE'}]}
        ).execute()

    # Create a response that's all good
    response = make_response(json.dumps('Successfully connected user.', 200))
    response.headers['Content-Type'] = 'application/json'
    return response


@glassdailycard.route('/disconnect', methods=['POST'])
def disconnect():
    """Disconnect the user from the application."""
    credentials = session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected.', 401))
        response.headers['Content-Type'] = 'application/json'
        return response

    # Execute HTTP GET request to revoke current token.
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    http = httplib2.Http()
    result = http.request(url, 'GET')[0]

    if result['status'] == '200':
        
        # Delete our user from CredentialsModel
        userid = credentials.id_token['sub']
        _credentials_for_user(userid).delete()

        # Delete our user from UserProperties
        user_properties = ndb.Key(UserProperties, userid).get()
        user_properties.key.delete()

        del session['credentials']
        del session['user_id']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

@glassdailycard.route('/dailyjob')
def dailyjob():
    """Ensure that the request is correct in every way."""

    # Get today's card
    today = datetime.date.today()
    query_get_todays_card = CronCards.query(CronCards.date == today)

    # Fetch one result from the query
    result_get_todays_card = query_get_todays_card.get()

    # Do we have a card to send today?
    if result_get_todays_card is not None:
            
        # Setup our Timeline Card body
        # We assume for example's sake that it's text
        timelinecard_body = {
            'notification': {'level': 'DEFAULT'},
            'text': result_get_todays_card.card,
            'menuItems': [{'action': 'DELETE'}]
        }

        #
        # This is the most basic way possible to do this.
        # If you're running large numbers of users, you should be batching
        # to cut your HTML:
        # https://developers.google.com/glass/batch
        #
        query_get_users = UserProperties.query()
        for user in query_get_users.fetch():
            #
            # Why UserProperties? Because you should not be spamming your
            # users on Glass if they don't want cards!
            #
            # Define your properties, make Glassware better.
            #

            # Get the credentials for the user
            user_credentials = _credentials_for_user(user.key.id()).get()

            # Send a card
            _authorized_mirror_service(user_credentials).timeline().insert(body=timelinecard_body).execute()

    response = make_response("{}", 200)
    response.headers['Content-Type'] = 'application/json'
    return response

@glassdailycard.route('/samplesforcron')
def samplesforcron():
    """Injects a single sample card so you can edit in the Datastore"""

    # Get today's card
    today = datetime.date.today()

    CronCards(card="Your daily card today is a sample!", date=today).put()

    response = make_response("Inserted sample card. Check your CronCards entity in the Datastore viewer.", 200)
    response.headers['Content-Type'] = 'text/html'
    return response