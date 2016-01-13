App Engine application for the Udacity training course.

## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [Google Cloud Endpoints][3]

## Task 1: Add Sessions to a Conference
- `Session` entity is setup to have the following properties:
  - `name` - Name of Session (StringProperty)
  - `sessionType` - Type of Session, such as workshop, lecture, etc (StringProperty)
  - `organizerUserId` - User ID who created the session, same as the one who created
    the parent conference (IntegerProperty)
  - `speakerId` - An unique identifier of the speaker who hosts the session
    (IntegerProperty)
  - `highlight` - Summary of the session (StringProperty, not indexed)
  - `date` - Date when the session take places (DateProperty)
  - `startTime` - Time when the session take places (TimeProperty)
  - `duration_minutes` - Length of the session in minutes (IntegerProperty)
- A conference's `websafeConferenceKey` is needed when creating a new session that
  is part of the conference. The session is created as a child of the
  conference, provided the user who created it also created the parent
  conference. This ancestor relationship is implemented since it makes querying
  a list of sessions within a conference a lot simpler
- The property `speakerId` within Session entity is used to identified the speaker
  as an entity. The `Speaker` entity has the following properties:
  - `displayName` - Full name of the speaker (StringProperty)
  - `mainEmail` - Speaker's e-mail address (StringProperty)
  - Instead of creating a speaker key using the speaker's name or e-mail address,
    the application opted for letting Datastore to generate the key automatically.
    This is done to ensure privacy as the key is passed via path and this could
    expose the speaker identity to unintended parties
  - The Speaker is defined as a entity instead of a string belonged to Session
    Entity. This is done to ensure development flexibility in the future. Even
    though there are only two properties right now, as development goes on it's
    possible to include more properties that could be useful to the application
    where a simple string property could not support
- The following endpoints API have been defined:
  - `createSession(SessionForm, websafeConferenceKey)` - Given a SessionForm and
    the parent's `websafeConferenceKey`, create a session as a child of the
    Conference
  - `getSession(websafeSessionKey)` - Given a `websafeSessionKey`, return the
    corresponding session
  - `updateSession(SessionForm, websafeSessionKey)` - Given a `websafeSessionKey`,
    return an updated session
  - `getConferenceSessions(websafeConferenceKey)` - Given a parent conference's
    `websafeConferenceKey`, return all children sessions
  - `getConferenceSessionsByType(websafeConferenceKey, sessionType)` - Given a
    parent conference's `websafeConferenceKey`, return all children sessions of a
    specific session type (workshop, lecture, etc)
  - `getSessionsBySpeaker(speakerId)` - Given a `speakerId`, return all sessions
    given by this particular speaker, across all conferences

## Task 2: Add Sessions to User Wishlist
- To accommodate user wishlist, the `Profile` entity was modified to include a
  new property - `sessionKeysToAttend`, a list of all the Sessions'
  `websafeSessionKey` a user has put into his or her wishlist. There is no need to
  create wishlist as a brand new entity since it is simply a list of sessions
  the user wishes to attend, which is similar to a list of conferences the user
  has registered to attend. A string list stored in the `Profile` entity allows
  easy querying and retrieving of all the session keys and their corresponding
  session entities
- The following endpoints API have been defined to implement this new option:
  - `addSessionToWishList(websafeSessionKey)` - Add the given `websafeSessionKey`
    to the user's sessions wishlist within their `Profile` entity, provided the
    user has already registered to attend the parent conference
  - `deleteSessionInWishlist(websafeSessionKey)` - Remove the given
    `websafeSessionKey` from the user's session wishlist
  - `getSessionsInWishlist` - Query all the sessions across all the conferences
    the user has added to their wishlist

## Task 3: Work on indexes and queries
- Several queries have been added that would be useful for this application
  - `querySimilarConferences(websafeConferenceKey, field, operator, value)` -
    Given a Conference entity, return a list of Conference entities that are
    created by the same user and have the property defined by the field,
    operator, and value. For example, a particular conference listing could
    include "Conferences by the same host that are near this location" by
    querying with city in `field`, EQ in `operator`, and the current conference
    city in `value`. Another example would be "Conferences by the same host
    you may like" by querying with topics in `field`, EQ in `operator`, and
    the current conference topics in `value`
  - `querySessionLength(websafeConferenceKey, field, operator, value)` - Given
    a Conference entity, return a list of session entities that are less than,
    more than, or equal to a defined duration (in minutes). For example, a user
    could look for sessions within a conference that are less than 120 minutes (
    2 hours) or more than 60 minutes (1 hour). In these cases, `field` is
    duration_minutes, `operator` could be LT,LTEQ,GT,GTEQ, or EQ, and `value` is
    the session length in minutes
  - `querySessionTime(websafeConferenceKey, sessionType, field, operator,value)` - To
    handle a query for all non-workshop sessions before 7pm, we
    have to understand what makes this query troublesome. This query is
    essentially two inequality filters: first on `sessionType`, then on
    `startTime`. The limitation of querying in Datastore is that inequality
    filters are limited to at most one property to avoid having to scan the
    entire index. The workaround is to make one of the inequality filter into an
    equality filter, or in this solution, "a member of" filter (IN). Instead of
    defining what the user doesn't want, we could structure the query to find
    sessions that are anything but workshop. For example if there are types such
    as workshop, lecture, seminar, the query would be `Session.sessionType.IN(['lecture','seminar'])` - 
    then anything but workshop will show up. Since the
    first filter is no longer inequality filter, the second filter could remain
    as is to filter out sessions before 7 pm. To use this query, all types of
    sessions but workshop will be supplied to `sessionType`, with `field` equal
    to startTime, `operator` could be anything the user wants, and `value` equal
    to the hour user specified (military hour, e.g. 7pm = 19)

## Task 4: Add a Task
- When a new session is added to a conference (via `createSession` endpoint), a
  task is added to the default queue with `websafeConferenceKey` and `speakerId`
  passed to `checkedFeaturedSpeaker` (located in main.py) as parameters. There,
  it's checked whether the speaker is present in more than one session within
  the same conference. If so, the speaker becomes a "Featured Speaker" and a new
  Memcache entry will be set to include the speaker name and the sessions he or
  she will be hosting
- `getFeaturedSpeaker` is also defined to easily access the featured speaker, if
  any


[1]: https://developers.google.com/appengine
[2]: http://python.org
[3]: https://developers.google.com/appengine/docs/python/endpoints/
