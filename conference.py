#!/usr/bin/env python

"""
conference.py -- Udacity conference server-side Python App Engine API;
uses Google Cloud Endpoints

API endpoints definition and helper functions

"""

from datetime import datetime, timedelta

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb
from google.net.proto.ProtocolBuffer import ProtocolBufferDecodeError

from containers import CONF_GET_REQUEST, CONF_GET_SIMILAR, CONF_POST_REQUEST
from containers import CREATE_SESSION, SESSION_GET_REQUEST, SESSION_POST_REQUEST
from containers import SESSIONS_GET_REQUEST, SESSION_QUERY_TYPE
from containers import SESSION_QUERY_TIME, SPEAKER_GET_REQUEST, SPEAKER_BY_NAME

from models import ConflictException
from models import Profile, ProfileMiniForm, ProfileForm
from models import StringMessage, BooleanMessage
from models import Conference, ConferenceForm, ConferenceForms
from models import ConferenceQueryForm, ConferenceQueryMiniForm
from models import ConferenceQueryForms
from models import TeeShirtSize
from models import Session, SessionForm, SessionForms, SessionQueryForm
from models import Speaker, SpeakerForm, SpeakerForms

from settings import WEB_CLIENT_ID, ANDROID_CLIENT_ID, IOS_CLIENT_ID
from settings import ANDROID_AUDIENCE
from settings import MEMCACHE_ANNOUNCEMENTS_KEY, MEMCACHE_SPEAKER_KEY
from settings import ANNOUNCEMENT_TPL
from settings import DEFAULTS, SESSION_DEFAULTS, OPERATORS, FIELDS

from utils import getUserId

__author__ = 'wiseleywu@gmail.com (Wiseley Wu)'

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# def user_authentication(func):
#     """Decorator to authenticate a user during API call"""
#
#     def login_user(self, *args, **kwargs):
#         user = endpoints.get_current_user()
#         if not user:
#             raise endpoints.UnauthorizedException('Please login first')
#         user_id = getUserId(user)
#         p_key = ndb.Key(Profile, user_id)
#         profile = p_key.get()
#         if not profile:
#             raise endpoints.UnauthorizedException(
#                 'Profile not found. Please try to relogin or re-register'
#                 )
#         return login_user


@endpoints.api(
    name='conference', version='v1', audiences=[ANDROID_AUDIENCE],
    allowed_client_ids=[WEB_CLIENT_ID,
                        API_EXPLORER_CLIENT_ID,
                        ANDROID_CLIENT_ID,
                        IOS_CLIENT_ID],
    scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""


# - - - Conference objects - - - - - - - - - - - - - - - - -

    def _copyConferenceToForm(self, conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf

    # @user_authentication
    def _createConferenceObject(self, request):
        """Create Conference object, returning ConferenceForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("Conference 'name' "
                                                "field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing
        # (both data model & outbound Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects;

        if data['startDate']:
            data['startDate'] = datetime.strptime(
                                    data['startDate'][:10], "%Y-%m-%d").date()
            # set month based on start_date
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(
                                    data['endDate'][:10], "%Y-%m-%d").date()
        # set seatsAvailable to be same as maxAttendees on creation
        if data["maxAttendees"] > 0 and data["seatsAvailable"] is None:
            data["seatsAvailable"] = data["maxAttendees"]
        # generate Profile Key based on user ID and Conference
        # ID based on Profile key get Conference key from ID
        p_key = ndb.Key(Profile, user_id)
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        c_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference, send email to organizer confirming
        # creation of Conference & return (modified) ConferenceForm
        Conference(**data).put()
        taskqueue.add(
            params={'email': user.email(),
                    'conferenceInfo': repr(request)},
            url='/tasks/send_confirmation_email'
        )
        return request

    @ndb.transactional()
    def _updateConferenceObject(self, request):
        """Update Conference object, returning ConferenceForm"""
        # authenticate user
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        # get conference object from Datastore
        conf = self._getDataStoreObject(request.websafeConferenceKey)
        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # Not getting all the fields, so don't create a new object; just
        # copy relevant fields from ConferenceForm to Conference object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name in ('startDate', 'endDate'):
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                    if field.name == 'startDate':
                        conf.month = data.month
                # write to Conference object
                setattr(conf, field.name, data)
        conf.put()
        prof = ndb.Key(Profile, user_id).get()
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(
            ConferenceForm, ConferenceForm, path='createConference',
            http_method='POST', name='createConference')
    def createConference(self, request):
        """Create a new conference."""
        return self._createConferenceObject(request)

    @endpoints.method(
            CONF_POST_REQUEST, ConferenceForm,
            path='conferences/{websafeConferenceKey}',
            http_method='PUT', name='updateConference')
    def updateConference(self, request):
        """Update conference w/provided fields & return w/updated info."""
        return self._updateConferenceObject(request)

    @endpoints.method(
            CONF_GET_REQUEST, ConferenceForm,
            path='conferences/{websafeConferenceKey}',
            http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get conference object from Datastore
        conf = self._getDataStoreObject(request.websafeConferenceKey)
        # get parent's profile
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(
            message_types.VoidMessage, ConferenceForms,
            path='getConferencesCreated',
            http_method='POST', name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
        # authenticate user
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # create ancestor query for all key matches for this user
        confs = Conference.query(ancestor=ndb.Key(Profile, user_id))
        prof = ndb.Key(Profile, user_id).get()
        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(
                conf, getattr(prof, 'displayName')) for conf in confs]
        )

    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(filtr["field"],
                                                   filtr["operator"],
                                                   filtr["value"])
            q = q.filter(formatted_query)
        return q

    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name)
                     for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException("Filter contains invalid "
                                                    "field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation been used in previous filters
                # disallow the filter if inequality was performed on a different
                # field before
                # track the field on which the inequality operation is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException(
                            "Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)

    @endpoints.method(
            ConferenceQueryForms, ConferenceForms,
            path='queryConferences',
            http_method='POST',
            name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # need to fetch organiser displayName from profiles
        # get all keys and use get_multi for speed
        organisers = [(ndb.Key(Profile, conf.organizerUserId))
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
                items=[
                    self._copyConferenceToForm(conf,
                                               names[conf.organizerUserId]
                                               ) for conf in conferences]
                )

    @endpoints.method(
            CONF_GET_SIMILAR, ConferenceForms,
            path='querySimilarConferences/{websafeConferenceKey}',
            http_method='POST',
            name='querySimilarConferences')
    def querySimilarConferences(self, request):
        """Query for similar conferences by the same creator."""
        # get conference object from Datastore
        conf = self._getDataStoreObject(request.websafeConferenceKey)
        # get parent's profile
        prof = conf.key.parent().get()
        # use ancestor query to get conferences by same creator,
        # then filter out the conference user provided
        conferences = Conference.query(ancestor=prof.key).filter(
                                                    Conference.key != conf.key)

        # Create filterNode and perform search if all fields are provided
        if (request.field and request.operator and request.value):
            node = ndb.query.FilterNode(request.field,
                                        OPERATORS[request.operator],
                                        request.value)
            conferences = conferences.filter(node)

        # Raise error if user didn't provide all 3 fields,
        # otherwise return current query result without further filtering
        elif (request.field or request.operator or request.value):
            raise endpoints.BadRequestException(
                                "You need to define field, operator, and value")

        return ConferenceForms(
                items=[
                    self._copyConferenceToForm(conf,
                                               prof.mainEmail
                                               ) for conf in conferences]
        )

# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert key objects to websafekey, put it back in a list
                if field.name.endswith('Attend'):
                    key_list = [x.urlsafe() for x in getattr(prof, field.name)]
                    setattr(pf, field.name, key_list)
                # convert t-shirt string to Enum;
                elif field.name == 'teeShirtSize':
                    setattr(pf, field.name,
                            getattr(TeeShirtSize, getattr(prof, field.name)))
                # just copy others
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf

    def _getProfileFromUser(self):
        """
        Return user Profile from datastore, creating new one if non-existent.
        """
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get Profile from datastore
        user_id = getUserId(user)
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get()
        # create new Profile if not there
        if not profile:
            profile = Profile(
                key=p_key,
                displayName=user.nickname(),
                mainEmail=user.email(),
                teeShirtSize=str(TeeShirtSize.NOT_SPECIFIED),
            )
            profile.put()

        return profile      # return Profile

    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()

        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
                        # if field == 'teeShirtSize':
                        #    setattr(prof, field, str(val).upper())
                        # else:
                        #    setattr(prof, field, val)
                        prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)

    @endpoints.method(
            message_types.VoidMessage, ProfileForm,
            path='profiles', http_method='GET', name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()

    @endpoints.method(
            ProfileMiniForm, ProfileForm,
            path='profiles', http_method='POST', name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)


# - - - Announcements - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = ANNOUNCEMENT_TPL % (
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement

    @endpoints.method(
            message_types.VoidMessage, StringMessage,
            path='conference/announcement/get',
            http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        return StringMessage(
            data=memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY) or "")


# - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        # get user Profile
        prof = self._getProfileFromUser()
        # get conference object from Datastore
        conf = self._getDataStoreObject(request.websafeConferenceKey)
        # register
        if reg:
            # check if user already registered otherwise add
            if conf.key in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(conf.key)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if conf.key in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(conf.key)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)

    @endpoints.method(
            message_types.VoidMessage, ConferenceForms,
            path='conferences/attending',
            http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        # get user Profile
        prof = self._getProfileFromUser()
        # get multiple conferences with multiple keys at once
        conferences = ndb.get_multi(prof.conferenceKeysToAttend)
        # get organizers
        organisers = [
            ndb.Key(Profile, conf.organizerUserId) for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(
                conf, names[conf.organizerUserId]) for conf in conferences]
        )

    @endpoints.method(
            CONF_GET_REQUEST, BooleanMessage,
            path='conferences/{websafeConferenceKey}',
            http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)

    @endpoints.method(
            CONF_GET_REQUEST, BooleanMessage,
            path='conferences/{websafeConferenceKey}',
            http_method='DELETE', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, reg=False)

    @endpoints.method(
            message_types.VoidMessage, ConferenceForms,
            path='filterPlayground',
            http_method='GET', name='filterPlayground')
    def filterPlayground(self, request):
        """Filter Playground"""
        q = Conference.query()
        # field = "city"
        # operator = "="
        # value = "London"
        # f = ndb.query.FilterNode(field, operator, value)
        # q = q.filter(f)
        q = q.filter(Conference.city == "London")
        q = q.filter(Conference.topics == "Medical Innovations")
        q = q.filter(Conference.month == 6)

        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "") for conf in q]
        )

# - - - Session - - - - - - - - - - - - - - - - - - - -

    def _copySessionToForm(self, session):
        """Copy relevant fields from Session to SessionForm."""
        sf = SessionForm()
        for field in sf.all_fields():
            if hasattr(session, field.name):
                # convert time to time string; just copy others
                if field.name in ['date', 'startTime']:
                    setattr(sf, field.name, str(getattr(session, field.name)))
                else:
                    setattr(sf, field.name, getattr(session, field.name))
            elif field.name == "websafeKey":
                setattr(sf, field.name, session.key.urlsafe())
        sf.check_initialized()
        return sf

    def _createSessionObject(self, request):
        """Create Session object, returning SessionForm"""
        # User authentication
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)
        # get conference object from Datastore
        conf = self._getDataStoreObject(request.websafeConferenceKey)

        # User Authorization
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can add session to the conference')

        # Copy SessionForm Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        wsck = data['websafeConferenceKey']
        del data['websafeKey']
        del data['websafeConferenceKey']

        # add default values for fields that aren't provided
        for df in SESSION_DEFAULTS:
            if data[df] in (None, []):
                data[df] = SESSION_DEFAULTS[df]
                setattr(request, df, SESSION_DEFAULTS[df])
        if data['date']:
            data['date'] = datetime.strptime(
                                    data['date'][:10], "%Y-%m-%d").date()
        if data['startTime']:
            data['startTime'] = datetime.strptime(
                                        data['startTime'], "%H:%M").time()

        # generate session Key based on conference Key
        c_key = conf.key
        s_id = Session.allocate_ids(size=1, parent=c_key)[0]
        s_key = ndb.Key(Session, s_id, parent=c_key)
        data['key'] = s_key
        Session(**data).put()

        # Run queue to check featured speaker if speaker ID is provided
        if data['speakerId']:
            speaker = ndb.Key(Speaker, data['speakerId']).get()
            if not speaker:
                raise endpoints.NotFoundException(
                    'No speaker found with this id')
            taskqueue.add(params={'wsck': wsck, 'speakerId': data['speakerId']},
                          url='/tasks/check_featured_speaker'
                          )
        return self._copySessionToForm(s_key.get())

    def _updateSessionObject(self, request):
        """Update Session object, returning SessionForm"""
        # User authentication
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # Copy SessionForm Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        # get session object from Datastore
        session = self._getDataStoreObject(request.websafeSessionKey)

        # User Authorization
        conf = session.key.parent().get()
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the session.')

        # copy relevant fields from Session Form to Session object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                if field.name == 'date':
                    data = datetime.strptime(data[:10], "%Y-%m-%d").date()
                if field.name == 'startTime':
                    data = datetime.strptime(data, "%H:%M").time()
                setattr(session, field.name, data)
        session.put()
        return self._copySessionToForm(session)

    def _sessionRegistration(self, request, reg=True):
        """
        Given a session, either put it in or remove it from a user's wishlist.

        Arg:
            reg (Default=True): If true, add the session to user's wishlist
                                If false, remove the session from user's
                                wishlit.
        Return:
            retval(Boolean): If ture, the operation (addition or removal of
                             session from user's wishlist) is successful
        """
        retval = None
        # User authentication
        prof = self._getProfileFromUser()

        # get session object from Datastore
        wssk = request.websafeSessionKey
        session = self._getDataStoreObject(wssk)

        # check whether user has registered for conference where session belongs
        c_key = session.key.parent()
        if c_key not in prof.conferenceKeysToAttend:
            raise ConflictException(
                "You have yet to register for the conference where this "
                "session will take place")

        # put session in wishlist
        if reg:
            if session.key in prof.sessionKeysToAttend:
                raise ConflictException(
                    "You have already placed this session in your wishlist")
            prof.sessionKeysToAttend.append(session.key)
            retval = True

        # remove session from wishlist
        else:
            if session.key not in prof.sessionKeysToAttend:
                raise ConflictException(
                    "This session was not in your wishlist. No action taken.")
            prof.sessionKeysToAttend.remove(session.key)
            retval = True
        prof.put()
        return BooleanMessage(data=retval)

    def _getSessionInWishlist(self, request):
        """Return a list of sessions within the user's wishlist."""
        # User authentication
        prof = self._getProfileFromUser()
        # Retrieve all sessions with all session Keys at once
        sessions = ndb.get_multi(prof.sessionKeysToAttend)
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
            CREATE_SESSION, SessionForm, path='createSession',
            http_method='POST', name='createSession')
    def createSession(self, request):
        """Create a new Session Object."""
        return self._createSessionObject(request)

    @endpoints.method(
            SESSION_POST_REQUEST, SessionForm,
            path='sessions/{websafeSessionKey}',
            http_method='PUT', name='updateSession')
    def updateSession(self, request):
        """Update session w/provided fields & return w/updated info."""
        return self._updateSessionObject(request)

    @endpoints.method(
            SESSION_GET_REQUEST, SessionForm,
            path='sessions/{websafeSessionKey}',
            http_method='GET', name='getSession')
    def getSession(self, request):
        """Return requested session (by websafeSessionKey)."""
        session = self._getDataStoreObject(request.websafeSessionKey)
        return self._copySessionToForm(session)

    @endpoints.method(
            SESSIONS_GET_REQUEST, SessionForms,
            path='conferences/{websafeConferenceKey}/sessions',
            http_method='GET', name='getConferenceSessions')
    def getConferenceSessions(self, request):
        """Return sessions given a websafeConferenceKey"""
        # get conference object from Datastore
        conf = self._getDataStoreObject(request.websafeConferenceKey)
        # query sessions using ancestor conference Key
        sessions = Session.query(ancestor=conf.key)
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
            SESSION_QUERY_TYPE, SessionForms,
            path='conferences/{websafeConferenceKey}/sessions/{type}',
            http_method='GET', name='getConferenceSessionsByType')
    def getConferenceSessionsByType(self, request):
        """Return sessions given a session type"""
        # get conference object from Datastore
        conf = self._getDataStoreObject(request.websafeConferenceKey)
        # query sessions using ancestor conference Key
        sessions = Session.query(ancestor=conf.key)
        # filter sessions by sessionType
        sessions = sessions.filter(
                        getattr(Session, 'sessionType') == request.type)
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
            CONF_GET_SIMILAR, SessionForms,
            path='conferences/{websafeConferenceKey}/sessions/duration',
            http_method='POST', name='querySessionLength')
    def querySessionLength(self, request):
        """Return sessions given a conference object and duration (minutes)"""
        # get conference object from Datastore
        conf = self._getDataStoreObject(request.websafeConferenceKey)
        # query sessions using ancestor conference Key and order by duration
        sessions = Session.query(ancestor=conf.key).order(
                                                    Session.duration_minutes)
        # temp workaroud since the 2nd filter clause picks up all sessions even
        # if the data=None
        sessions = sessions.filter(Session.duration_minutes != None)

        # create filterNode and perform filter if all fields are provided
        if (request.operator and request.value):
            node = ndb.query.FilterNode('duration_minutes',
                                        OPERATORS[request.operator],
                                        request.value
                                        )
            sessions = sessions.filter(node)
        else:
            raise endpoints.BadRequestException(
                "You need to define both operator and value")

        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
            SESSION_QUERY_TIME, SessionForms,
            path='conferences/{websafeConferenceKey}/sessions/time',
            http_method='POST', name='querySessionTime')
    def querySessionTime(self, request):
        """Return sessions given a conference object, time and type"""
        # get conference object from Datastore
        conf = self._getDataStoreObject(request.websafeConferenceKey)
        # query sessions using ancestor conf Key, order sessions by start time
        sessions = Session.query(ancestor=conf.key).order(Session.startTime)

        # filter sessions by time (before/after/equal certain time)
        if (request.operator and request.time):
            node = ndb.query.FilterNode(
                                    'startTime',
                                    OPERATORS[request.operator],
                                    datetime(1970, 01, 01, request.time, 00))
            sessions = sessions.filter(node)
        else:
            raise endpoints.BadRequestException("You need to define both "
                                                "operator and time")

        # only return session types that are not equal to what the user provided
        return SessionForms(
            items=[self._copySessionToForm(x)
                   for x in sessions
                   if x.sessionType != request.sessionType]
        )

    # WORKAROUND of above endpoints that fully utilize Datastore queries

    # @endpoints.method(SESSION_QUERY_TIME, SessionForms,
    #         path='querySessionTime/{websafeConferenceKey}',
    #         http_method='POST', name='querySessionTime')
    # def querySessionTime(self, request):
    #     """Return sessions given a conference object, time and type"""
    # try:
    #     conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
    # except ProtocolBufferDecodeError:
    #     raise endpoints.NotFoundException(
    #         'No conference found with key: %s' %
    #         request.websafeConferenceKey)
    #     typeList=[item for item in request.sessionType]
    #     if typeList:
    #         sessions = Session.query(
    #                       Session.sessionType.IN(typeList),
    #                       ancestor=conf.key).order(Session.startTime)
    #     else:
    #         sessions = Session.query(
    #                       ancestor=conf.key).order(Session.startTime)
    #     if (request.operator and request.time):
    #         node = ndb.query.FilterNode(
    #                           'startTime',
    #                           OPERATORS[request.operator],
    #                           datetime(1970,01,01,request.time,00))
    #         sessions = sessions.filter(node)
    #     elif (request.operator or request.time):
    #         raise endpoints.BadRequestException("You need to define both "
    #                                             "operator and time")
    #     return SessionForms(
    #         items=[self._copySessionToForm(session) for session in sessions]
    #     )

    @endpoints.method(
            SPEAKER_GET_REQUEST, SessionForms,
            path='sessions/speakers/{speakerId}',
            http_method='GET', name='getSessionsBySpeaker')
    def getSessionsBySpeaker(self, request):
        """Return sessions given a speakerId"""
        # get speaker object from Datastore
        speaker = ndb.Key(Speaker, request.speakerId).get()
        # query speaker by id
        sessions = Session.query().filter(
                            getattr(Session, 'speakerId') == request.speakerId)
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
            SESSION_GET_REQUEST, BooleanMessage,
            path='profile/wishlist/{websafeSessionKey}',
            http_method='POST', name='addSessionToWishList')
    def addSessionToWishList(self, request):
        """Add Session to the user's wishlist."""
        return self._sessionRegistration(request)

    @endpoints.method(
            SESSION_GET_REQUEST, BooleanMessage,
            path='profile/wishlist/{websafeSessionKey}',
            http_method='DELETE', name='deleteSessionInWishlist')
    def deleteSessionInWishlist(self, request):
        """Remove session from user's wishlist."""
        return self._sessionRegistration(request, reg=False)

    @endpoints.method(
            message_types.VoidMessage, SessionForms,
            path='profile/wishlist',
            http_method='GET', name='getSessionsInWishlist')
    def getSessionsInWishlist(self, request):
        """Query for all the sessions the user has placed in wishlist."""
        return self._getSessionInWishlist(request)

# - - - Speaker - - - - - - - - - - - - - - - - - - - -

    def _copySpeakerToForm(self, speaker):
        """Copy relevant fields from Speaker to SpeakerForm."""
        sf = SpeakerForm()
        for field in sf.all_fields():
            # retrieve speaker ID and display on SpeakerForm
            if field.name == 'speakerId':
                sf.speakerId = speaker.key.integer_id()
            # copy other fields
            elif hasattr(speaker, field.name):
                setattr(sf, field.name, getattr(speaker, field.name))
        sf.check_initialized()
        return sf

    def _createSpeakerObject(self, request):
        """Create Speaker Object, returning SessionForm/request."""
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['speakerId']
        key = Speaker(**data).put()
        return self._copySpeakerToForm(key.get())

    @endpoints.method(
            SpeakerForm, SpeakerForm, path='createSpeaker',
            http_method='POST', name='createSpeaker')
    def createSpeaker(self, request):
        """Create new speaker."""
        return self._createSpeakerObject(request)

    @endpoints.method(
            SPEAKER_GET_REQUEST, SpeakerForm, path='speaker/{speakerId}',
            http_method='GET', name='getSpeaker')
    def getSpeaker(self, request):
        """Get Speaker Object given the speakerId"""
        speaker = ndb.Key(Speaker, request.speakerId).get()
        return self._copySpeakerToForm(speaker)

    @endpoints.method(
            SPEAKER_BY_NAME, SpeakerForms, path='speakers/{name}',
            http_method='GET', name='getSpeakerByName')
    def getSpeakerByName(self, request):
        """Get Speaker Object given the speaker's full name"""
        speakers = Speaker.query().filter(Speaker.displayName == request.name)
        return SpeakerForms(
            items=[self._copySpeakerToForm(speaker) for speaker in speakers]
        )

    @endpoints.method(
            message_types.VoidMessage, SpeakerForms,
            path='speakers/all',
            http_method='GET', name='getSpeakersCreated')
    def getSpeakersCreated(self, request):
        """Get all Speaker Objects within Datastore"""
        speakers = Speaker.query()
        return SpeakerForms(
            items=[self._copySpeakerToForm(speaker) for speaker in speakers]
        )

    @endpoints.method(
            message_types.VoidMessage, StringMessage,
            path='conference/featured_speaker/get',
            http_method='GET', name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """Return featured speaker from memcache."""
        return StringMessage(data=memcache.get(MEMCACHE_SPEAKER_KEY) or "")

    @staticmethod
    def _getDataStoreObject(websafekey):
        """
        Retrieve Datastore objects using websafeKey

        Args:
            websafekey (string): websafekey used to retrieve object
        Returns:
            entity (GAE entities): retrieved object from Datastore
        """
        # try getting object from datastore using websafekey
        try:
            entity = ndb.Key(urlsafe=websafekey).get()
        # raise error if websafekey isn't valid (no object found)
        except (ProtocolBufferDecodeError, TypeError):
            raise endpoints.NotFoundException(
                'No object found with key: %s' % websafekey)
        return entity

api = endpoints.api_server([ConferenceApi])  # register API
