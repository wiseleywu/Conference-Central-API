#!/usr/bin/env python

"""settings.py

Udacity conference server-side Python App Engine app user settings

Contains global constants such as client ID, memcache key, default values for
Datastore models, and dictionary for Datastore queries

"""

__author__ = 'wiseleywu@gmail.com (Wiseley Wu)'

# Replace the following lines with client IDs obtained from the APIs
# Console or Cloud Console.
WEB_CLIENT_ID = 'INSERT_WEB_CLIENT_ID_HERE'
ANDROID_CLIENT_ID = 'replace with Android client ID'
IOS_CLIENT_ID = 'replace with iOS client ID'
ANDROID_AUDIENCE = WEB_CLIENT_ID

MEMCACHE_ANNOUNCEMENTS_KEY = "RECENT_ANNOUNCEMENTS"
MEMCACHE_SPEAKER_KEY = "FEATURED_SPEAKER"
ANNOUNCEMENT_TPL = ('Last chance to attend! The following conferences '
                    'are nearly sold out: %s')

DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": ["Default", "Topic"],
}

SESSION_DEFAULTS = {
    "sessionType": "Default Type",
    "highlight": "Default Highlight",
    "duration_minutes": None,
}

OPERATORS = {
            'EQ':   '=',
            'GT':   '>',
            'GTEQ': '>=',
            'LT':   '<',
            'LTEQ': '<=',
            'NE':   '!='
            }

FIELDS = {
            'CITY': 'city',
            'TOPIC': 'topics',
            'MONTH': 'month',
            'MAX_ATTENDEES': 'maxAttendees',
            }
