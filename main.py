#!/usr/bin/env python

"""
main.py -- Udacity conference server-side Python App Engine
    HTTP controller handlers for memcache & task queue access

$Id$

created by wesc on 2014 may 24

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'

import webapp2
from google.appengine.api import app_identity
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import ndb
from conference import ConferenceApi
from conference import MEMCACHE_SPEAKER_KEY
from models import Conference, Session, Speaker

class SetAnnouncementHandler(webapp2.RequestHandler):
    def get(self):
        """Set Announcement in Memcache."""
        ConferenceApi._cacheAnnouncement()
        self.response.set_status(204)


class SendConfirmationEmailHandler(webapp2.RequestHandler):
    def post(self):
        """Send email confirming Conference creation."""
        mail.send_mail(
            'noreply@%s.appspotmail.com' % (
                app_identity.get_application_id()),     # from
            self.request.get('email'),                  # to
            'You created a new Conference!',            # subj
            'Hi, you have created a following '         # body
            'conference:\r\n\r\n%s' % self.request.get(
                'conferenceInfo')
        )

class checkedFeaturedSpeaker(webapp2.RequestHandler):
    def post(self):
        """Check Featured Speaker within a Conference"""
        conf = ndb.Key(urlsafe=self.request.get('wsck')).get()
        speaker=ndb.Key(Speaker, int(self.request.get('speakerId'))).get()
        sessions = Session.query(ancestor=conf.key)
        sessions = sessions.filter(Session.speakerId == int(self.request.get('speakerId')))
        if sessions.count() <= 1:
            announcement=""
        else:
            announcement='%s %s %s %s' % (
                'Featured Speaker - ',
                speaker.displayName,
                '. You can find the speaker in the following sessions: ',
                ', '.join(
                session.name for session in sessions)
            )
        memcache.set(MEMCACHE_SPEAKER_KEY, announcement)
        self.response.set_status(204)



app = webapp2.WSGIApplication([
    ('/crons/set_announcement', SetAnnouncementHandler),
    ('/tasks/send_confirmation_email', SendConfirmationEmailHandler),
    ('/tasks/check_featured_speaker', checkedFeaturedSpeaker),
], debug=True)
