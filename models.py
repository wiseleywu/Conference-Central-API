#!/usr/bin/env python

"""models.py

Udacity conference server-side Python App Engine data & ProtoRPC models

Contains Datastore Models and MessageField Classes definition to support
API endpoints within conference.py

"""

import httplib
import endpoints
from protorpc import messages
from google.appengine.ext import ndb

__author__ = 'wiseleywu@gmail.com (Wiseley Wu)'


class ConflictException(endpoints.ServiceException):
    """ConflictException -- exception mapped to HTTP 409 response"""
    http_status = httplib.CONFLICT


class Profile(ndb.Model):
    """Profile -- User profile object"""
    displayName = ndb.StringProperty()
    mainEmail = ndb.StringProperty()
    teeShirtSize = ndb.StringProperty(default='NOT_SPECIFIED')
    conferenceKeysToAttend = ndb.StringProperty(repeated=True)
    sessionKeysToAttend = ndb.StringProperty(repeated=True)


class ProfileMiniForm(messages.Message):
    """ProfileMiniForm -- update Profile form message"""
    displayName = messages.StringField(1)
    teeShirtSize = messages.EnumField('TeeShirtSize', 2)


class ProfileForm(messages.Message):
    """ProfileForm -- Profile outbound form message"""
    displayName = messages.StringField(1)
    mainEmail = messages.StringField(2)
    teeShirtSize = messages.EnumField('TeeShirtSize', 3)
    conferenceKeysToAttend = messages.StringField(4, repeated=True)
    sessionKeysToAttend = messages.StringField(5, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    data = messages.StringField(1, required=True)


class BooleanMessage(messages.Message):
    """BooleanMessage-- outbound Boolean value message"""
    data = messages.BooleanField(1)


class Conference(ndb.Model):
    """Conference -- Conference object"""
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty()
    organizerUserId = ndb.StringProperty()
    topics = ndb.StringProperty(repeated=True)
    city = ndb.StringProperty()
    startDate = ndb.DateProperty()
    month = ndb.IntegerProperty()
    endDate = ndb.DateProperty()
    maxAttendees = ndb.IntegerProperty()
    seatsAvailable = ndb.IntegerProperty()


class ConferenceForm(messages.Message):
    """ConferenceForm -- Conference outbound form message"""
    name = messages.StringField(1)
    description = messages.StringField(2)
    organizerUserId = messages.StringField(3)
    topics = messages.StringField(4, repeated=True)
    city = messages.StringField(5)
    startDate = messages.StringField(6)
    month = messages.IntegerField(7, variant=messages.Variant.INT32)
    maxAttendees = messages.IntegerField(8, variant=messages.Variant.INT32)
    seatsAvailable = messages.IntegerField(9, variant=messages.Variant.INT32)
    endDate = messages.StringField(10)
    websafeKey = messages.StringField(11)
    organizerDisplayName = messages.StringField(12)


class ConferenceForms(messages.Message):
    """ConferenceForms -- multiple Conference outbound form message"""
    items = messages.MessageField(ConferenceForm, 1, repeated=True)


class TeeShirtSize(messages.Enum):
    """TeeShirtSize -- t-shirt size enumeration value"""
    NOT_SPECIFIED = 1
    XS_M = 2
    XS_W = 3
    S_M = 4
    S_W = 5
    M_M = 6
    M_W = 7
    L_M = 8
    L_W = 9
    XL_M = 10
    XL_W = 11
    XXL_M = 12
    XXL_W = 13
    XXXL_M = 14
    XXXL_W = 15


class ConferenceQueryForm(messages.Message):
    """ConferenceQueryForm -- Conference query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)


class ConferenceQueryMiniForm(messages.Message):
    """ConferenceQueryMiniForm -- Conference query inbound form message"""
    operator = messages.StringField(1)
    value = messages.IntegerField(2, variant=messages.Variant.INT32)


class ConferenceQueryForms(messages.Message):
    """
    ConferenceQueryForms -- multiple ConferenceQueryForm inbound form message
    """
    filters = messages.MessageField(ConferenceQueryForm, 1, repeated=True)


class Session(ndb.Model):
    """Session - Conference's Session Object"""
    name = ndb.StringProperty(required=True)
    sessionType = ndb.StringProperty()
    speakerId = ndb.IntegerProperty()
    highlight = ndb.StringProperty(indexed=False)
    date = ndb.DateProperty()
    startTime = ndb.TimeProperty()
    duration_minutes = ndb.IntegerProperty()


class SessionForm(messages.Message):
    """SessionForm -- Session outbound form message"""
    name = messages.StringField(1)
    sessionType = messages.StringField(2)
    speakerId = messages.IntegerField(3, variant=messages.Variant.INT32)
    highlight = messages.StringField(4)
    date = messages.StringField(5)
    startTime = messages.StringField(6)
    duration_minutes = messages.IntegerField(7, variant=messages.Variant.INT32)
    websafeKey = messages.StringField(8)


class SessionForms(messages.Message):
    """SessionForms -- multiple Session outbound form message"""
    items = messages.MessageField(SessionForm, 1, repeated=True)


class SessionQueryForm(messages.Message):
    """SessioneQueryForm -- Session query inbound form message"""
    sessionType = messages.StringField(1)
    operator = messages.StringField(2)
    time = messages.IntegerField(
        3, variant=messages.Variant.INT32, default=None)


class Speaker(ndb.Model):
    """Speaker -- Session Speaker Object"""
    displayName = ndb.StringProperty(required=True)
    mainEmail = ndb.StringProperty(required=True)
    # sessionKeysToAttend = ndb.StringProperty(repeated=True)


class SpeakerForm(messages.Message):
    """SpeakerForm -- Speaker outbound form message"""
    displayName = messages.StringField(1, required=True)
    mainEmail = messages.StringField(2)
    speakerId = messages.IntegerField(3, variant=messages.Variant.INT32)
    # sessionKeysToAttend = messages.StringField(3, repeated=True)


class SpeakerForms(messages.Message):
    """SpeakerForms -- multiple Speaker outbound form message"""
    items = messages.MessageField(SpeakerForm, 1, repeated=True)
