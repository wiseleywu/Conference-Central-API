#!/usr/bin/env python

"""containers.py

Udacity conference server-side Python App Engine data & ProtoRPC models

Define all ResourceContainer used in conference.py

"""

import endpoints
from protorpc import messages
from protorpc import message_types

from models import ConferenceForm, ConferenceQueryForm, ConferenceQueryMiniForm
from models import SessionForm, SessionQueryForm

__author__ = 'wiseleywu@gmail.com (Wiseley Wu)'


CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

CONF_GET_SIMILAR = endpoints.ResourceContainer(
    ConferenceQueryMiniForm,
    websafeConferenceKey=messages.StringField(1),
)

CONF_POST_REQUEST = endpoints.ResourceContainer(
    ConferenceForm,
    websafeConferenceKey=messages.StringField(1),
)

CREATE_SESSION = endpoints.ResourceContainer(
    SessionForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeSessionKey=messages.StringField(1),
)

SESSION_POST_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeSessionKey=messages.StringField(1),
)

SESSIONS_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_QUERY_TYPE = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
    type=messages.StringField(2),
)

SESSION_QUERY_TIME = endpoints.ResourceContainer(
    SessionQueryForm,
    websafeConferenceKey=messages.StringField(1),
)

SPEAKER_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    speakerId=messages.IntegerField(1, variant=messages.Variant.INT32,
                                    required=True),
)

SPEAKER_BY_NAME = endpoints.ResourceContainer(
    message_types.VoidMessage,
    name=messages.StringField(1),
)
