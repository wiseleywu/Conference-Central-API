## Conference Central API
App Engine application for the Udacity training course.

## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [Google Cloud Endpoints][3]

## Instructions
- [Download][4] and install Google App Engine SDK for Python
- Clone this repository
- Create a new project from [Google Developers Console][5]. An application ID will be assigned to your project
- Go to API Manager -> Credentials in the Developers Console to create an OAuth client ID for web application use (or others if you plan to test the APIs on Android/iOS platform)
- Update the value of `application` in [app.yaml](app.yaml) to the application ID you have registered in the Developers Console and would like to use to host your instance of this sample
- Update the values at the top of [settings.py](settings.py) to reflect the respective client IDs you have registered in the Developers Console
- Update the value of `CLIENT ID` at Line 89 in [static/js/app.js](static/js/app.js) to the Web client ID
- Deploy the app on to local web server by invoking the following command in console: `$ dev_appserver.py ConferenceCentral_Complete/`. Visit the local server address at [localhost:8080][6] (by default)
- In order to deploy the server successfully, you will have to tell the browser to allow active content via HTTP (on Chrome, click the shield in the URL bar and click "Load unsafe script")
- Upload the app to Google App Engine by invoking the following command in console: `$ appcfg.py -A YOUR_PROJECT_ID update ConferenceCentral_Complete/`. Visit the deployed application at https://YOUR_PROJECT_ID.appspot.com/

## Task 1: Add Sessions to a Conference
- `Session` entity is setup to have the following properties:
  - `name` - Name of Session (StringProperty)
  - `sessionType` - Type of Session, such as workshop, lecture, etc (StringProperty)
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
  new property - `sessionKeysToAttend`, a list of all the Sessions' keys
  a user has put into his or her wishlist. There is no need to
  create wishlist as a brand new entity since it is simply a list of sessions
  the user wishes to attend, which is similar to a list of conferences the user
  has registered to attend. A key list stored in the `Profile` entity allows
  easy retrieving of all the session keys and their corresponding
  session entities
- The following endpoints API have been defined to implement this new option:
  - `addSessionToWishList(websafeSessionKey)` - Add the corresponding Session
    key to the user's wishlist within their `Profile` entity, provided
    the user has already registered to attend the parent conference
  - `deleteSessionInWishlist(websafeSessionKey)` - Remove the corresponding
    Session key from the user's wishlist
  - `getSessionsInWishlist` - Retrieve all the sessions across all the
    conferences the user has added to his or her wishlist

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
  - `querySessionLength(websafeConferenceKey, operator, value)` - Given
    a Conference entity, return a list of session entities that are less than,
    more than, or equal to a defined duration (in minutes). For example, a user
    could look for sessions within a conference that are less than 120 minutes (
    2 hours) or more than 60 minutes (1 hour). In these cases,  `operator` could
    be LT,LTEQ,GT,GTEQ, or EQ, and `value` is the session length in minutes.
  - `querySessionTime(websafeConferenceKey, sessionType, operator,value)` - To
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
    sessions but workshop will be supplied to `sessionType`, `operator` could be
    anything the user wants, and `value` equal to the hour user specified
    (military hour, e.g. 7pm = 19).

    Another workaround is to handle the second search in python code. In the
    actual implementation of this query, a Datastore query is first executed to
    filter out undesired start time. Afterward, the filtered Datastore result is
    passed into a list comprehension with if/else statement, where only sessions
    with session type not equal to what the user specified will be passed to
    the final result. In this case, user supplied undesired session type to
    `sessionType`, while `operator` and `value` arguments remained the same as
    above.

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
[4]: https://cloud.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python
[5]: https://console.developers.google.com/
[6]: http://localhost:8080/
