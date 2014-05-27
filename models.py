"""
models.py

Models for App Engine datastore

"""
from google.appengine.ext import ndb

class UserProperties(ndb.Model):
    """Store whether a user wants email and/or weekend cards."""
    email = ndb.BooleanProperty(required=True)
    weekends = ndb.BooleanProperty(required=True)

class CronCards(ndb.Model):
    """Stores cards to be sent to user by Cron task"""
    card = ndb.TextProperty(required=True)
    date = ndb.DateProperty(required=True)
    created = ndb.DateTimeProperty(auto_now_add=True)