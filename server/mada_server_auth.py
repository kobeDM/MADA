#!/usr/bin/env python3

"""Login sessions, roles and CSRF. The session mechanism is modeled on
/home/msgc/repo/MPOD/web_backend/app/auth.py: a signed cookie via Starlette's
SessionMiddleware (configured in mada_server_app.py with
config['session_secret']), with no server-side session store -- the cookie
itself, verified by its signature, is the session. This differs from MPOD in
two ways the daq-server spec requires that MPOD doesn't have: two roles,
viewer/operator (2026-11-12_3.md section 3.5), and CSRF on state-changing
requests (section 6, double-submit cookie)."""

import secrets

import bcrypt
from fastapi import HTTPException, Request, Response
from starlette.requests import HTTPConnection

SESSION_USER_KEY = 'user'
CSRF_COOKIE = 'mada_csrf'

ROLE_VIEWER = 'viewer'
ROLE_OPERATOR = 'operator'

_DUMMY_HASH = bcrypt.hashpw(b'no-such-user', bcrypt.gensalt()).decode('ascii')


def verify_login(users, username, password):
    """`users` is the config's 'users' mapping (username -> {'password_hash',
    'role'}). Returns (username, role) on a match, else None. Checks a hash
    even when the user doesn't exist (a fixed dummy one) so both failure
    cases take the same time."""
    entry = users.get(username)
    hash_to_check = entry['password_hash'] if entry else _DUMMY_HASH
    ok = bcrypt.checkpw(password.encode('utf-8'), hash_to_check.encode('ascii'))
    return (username, entry['role']) if (entry and ok) else None


def current_user(conn: HTTPConnection):
    """{'username': ..., 'role': ...} from the session cookie, or None."""
    return conn.session.get(SESSION_USER_KEY)


def login(request: Request, username, role):
    request.session[SESSION_USER_KEY] = {'username': username, 'role': role}


def logout(request: Request):
    request.session.clear()


def require_user(request: Request):
    """FastAPI dependency for JSON/SSE endpoints: 401 when not logged in."""
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail='login required')
    return user


def require_operator(request: Request):
    user = require_user(request)
    if user['role'] != ROLE_OPERATOR:
        raise HTTPException(status_code=403, detail='operator role required')
    return user


def require_page_user(request: Request):
    """Like require_user, but for a page a browser navigates to: redirect to
    /login instead of a bare 401 (same trick as MPOD's require_page_login --
    FastAPI's default exception handler passes exc.headers through, so the
    browser follows the Location header on this 303)."""
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=303, headers={'Location': '/login'})
    return user


def issue_csrf_cookie(response: Response, cookie_secure):
    """Ensure a CSRF token cookie exists; call on every page render (cheap
    and idempotent from the browser's point of view when unchanged)."""
    token = secrets.token_urlsafe(32)
    response.set_cookie(CSRF_COOKIE, token, httponly=False, samesite='lax', secure=cookie_secure, path='/')
    return token


def require_csrf(request: Request):
    """FastAPI dependency for POST endpoints: the X-CSRF-Token header must
    match the mada_csrf cookie."""
    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get('X-CSRF-Token')
    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail='missing or invalid CSRF token')
