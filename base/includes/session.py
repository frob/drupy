# Id: session.inc,v 1.48 2008/04/16 11:35:51 dries Exp $
#

#
# @package Drupy
# @see http://drupy.net
# @note Drupy is a port of the Drupal project.
#  The Drupal project can be found at http://drupal.org
# @file session.py (ported from Drupal's session.inc)
#  User session handling functions.
# @author Brendon Crawford
# @copyright 2008 Brendon Crawford
# @contact message144 at users dot sourceforge dot net
# @created 2008-05-25
# @version 0.1
# @license: 
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

static('static_sessionsavesession_savesession')

def sess_open(save_path, session_name):
  return True


def sess_close():
  return True

def sess_read(key):
  global user
  # Write and Close handlers are called after destructing objects since PHP 5.0.5
  # Thus destructors can use sessions but session handler can't use objects.
  # So we are moving session closure before destructing objects.
  register_shutdown_function('session_write_close')
  # Handle the case of first time visitors and clients that don't store cookies (eg. web crawlers).
  if (not isset(_COOKIE, session_name())):
    user = drupal_anonymous_user()
    return ''
  # Otherwise, if the session is still active, we have a record of the client's session in the database.
  user = db_fetch_object(db_query("SELECT u.*, s.* FROM {users} u INNER JOIN {sessions} s ON u.uid = s.uid WHERE s.sid = '%s'", key))
  # We found the client's session record and they are an authenticated user
  if (user and user.uid > 0):
    # This is done to unserialize the data member of user
    user = drupal_unpack(user)
    # Add roles element to user
    user.roles = array()
    user.roles[DRUPAL_AUTHENTICATED_RID] = 'authenticated user'
    result = db_query("SELECT r.rid, r.name FROM {role} r INNER JOIN {users_roles} ur ON ur.rid = r.rid WHERE ur.uid = %d", user.uid)
    while True:
      role = db_fetch_object(result)
      if role == None:
        break
      user.roles[role.rid] = role.name
  # We didn't find the client's record (session has expired), or they are an anonymous user.
  else:
    session = (user.session if isset(user.session) else '')
    user = drupal_anonymous_user(session)
  return user.session



def sess_write(key, value):
  global user
  # If saving of session data is disabled or if the client doesn't have a session,
  # and one isn't being created (value), do nothing.
  if (not session_save_session() or (empty(_COOKIE[session_name()]) and empty(value))):
    return True
  result = db_result(db_query("SELECT COUNT(*) FROM {sessions} WHERE sid = '%s'", key))
  if (not result):
    # Only save session data when when the browser sends a cookie. This keeps
    # crawlers out of session table. This reduces memory and server load,
    # and gives more useful statistics. We can't eliminate anonymous session
    # table rows without breaking "Who's Online" block.
    if (user.uid or value or count(_COOKIE)):
      db_query("INSERT INTO {sessions} (sid, uid, cache, hostname, session, timestamp) VALUES ('%s', %d, %d, '%s', '%s', %d)", key, user.uid, (user.cache if isset(user, 'cache') else ''), ip_address(), value, drupy_time())
  else:
    db_query("UPDATE {sessions} SET uid = %d, cache = %d, hostname = '%s', session = '%s', timestamp = %d WHERE sid = '%s'", user.uid, (user.cache if isset(user, 'cache') else ''), ip_address(), value, drupy_time(), key)
    # Last access time is updated no more frequently than once every 180 seconds.
    # This reduces contention in the users table.
    if (user.uid and drupy_time() - user.access > variable_get('session_write_interval', 180)):
      db_query("UPDATE {users} SET access = %d WHERE uid = %d", time(), user.uid)
  return True



#
# Called when an anonymous user becomes authenticated or vice-versa.
#
def sess_regenerate():
  old_session_id = session_id()
  session_regenerate_id()
  db_query("UPDATE {sessions} SET sid = '%s' WHERE sid = '%s'", session_id(), old_session_id)


#
# Counts how many users have sessions. Can count either anonymous sessions, authenticated sessions, or both.
#
# @param int timestamp
#   A Unix timestamp representing a point of time in the past.
#   The default is 0, which counts all existing sessions.
# @param int anonymous
#   True counts only anonymous users.
#   False counts only authenticated users.
#   Any other value will return the count of both authenticated and anonymous users.
# @return  int
#   The number of users with sessions.
#
def sess_count(timestamp = 0, anonymous = True):
  query = (' AND uid = 0' if anonymous else ' AND uid > 0')
  return db_result(db_query('SELECT COUNT(sid) AS count FROM {sessions} WHERE timestamp >= %d' +  query, timestamp))


#
# Called by PHP session handling with the PHP session ID to end a user's session.
#
# @param  string sid
#   the session id
#
def sess_destroy_sid(sid):
  db_query("DELETE FROM {sessions} WHERE sid = '%s'", sid)



#
# End a specific user's session
#
# @param  string uid
#   the user id
#
def sess_destroy_uid(uid):
  db_query('DELETE FROM {sessions} WHERE uid = %d', uid)




def sess_gc(lifetime):
  # Be sure to adjust 'php_value session.gc_maxlifetime' to a large enough
  # value. For example, if you want user sessions to stay in your database
  # for three weeks before deleting them, you need to set gc_maxlifetime
  # to '1814400'. At that value, only after a user doesn't log in after
  # three weeks (1814400 seconds) will his/her session be removed.
  db_query("DELETE FROM {sessions} WHERE timestamp < %d", time() - lifetime)
  return True



#
# Determine whether to save session data of the current request.
#
# This function allows the caller to temporarily disable writing of session data,
# should the request end while performing potentially dangerous operations, such as
# manipulating the global user object.  See http://drupal.org/node/218104 for usage
#
# @param status
#   Disables writing of session data when False, (re-)enables writing when True.
# @return
#   False if writing session data has been disabled. Otherwise, True.
#
def session_save_session(status = None):
  global static_sessionsavesession_savesession
  if static_sessionsavesession_savesession == None:
    static_sessionsavesession_savesession = True
  if status != None:
    static_sessionsavesession_savesession = status
  return static_sessionsavesession_savesession

