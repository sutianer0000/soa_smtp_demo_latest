"""Google OAuth 2.0 Authorization Code flow, written by hand so every step is visible."""
import time
from urllib.parse import urlencode

import httpx

from . import config, db

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# openid + email -> who the user is (authentication)
# mail.google.com -> the only scope Gmail SMTP accepts for XOAUTH2 (authorization)
SCOPES = "openid email https://mail.google.com/"


def _json(resp: httpx.Response) -> dict:
    if resp.is_error:
        raise RuntimeError(f"Google returned {resp.status_code}: {resp.text}")
    return resp.json()


def authorization_url(state: str, login_hint: str | None = None) -> str:
    """Step 1: the Google page the browser is sent to, where the user signs in and consents."""
    params = {
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": config.REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",             # also give us a refresh_token
        "prompt": "consent select_account",   # always return a refresh_token; let the user pick an account
        "state": state,                       # anti-CSRF value, checked again in the callback
    }
    if login_hint:
        params["login_hint"] = login_hint
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> str:
    """Step 2 (server to Google): trade the one-time code for tokens. Returns the user's email."""
    tokens = _json(httpx.post(TOKEN_URL, data={
        "code": code,
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "redirect_uri": config.REDIRECT_URI,
        "grant_type": "authorization_code",
    }))
    #get token from google and get user info from google using the access token
    userinfo = _json(httpx.get(USERINFO_URL, headers={"Authorization": f"Bearer {tokens['access_token']}"}))
    email = userinfo["email"].lower()
    #save the user info in the database, including refresh token, access token and expiration time
    db.save_user(email, tokens.get("refresh_token"), tokens["access_token"], time.time() + tokens["expires_in"])
    return email


def access_token_for(email: str) -> str:
    """Step 3: a valid access token for this user, refreshed if expired (they last about 1 hour)."""
    user = db.get_user(email)
    if user is None:
        raise RuntimeError(f"{email} has not signed in to this app yet")
    if time.time() < user["expires_at"] - 60:
        return user["access_token"]

    tokens = _json(httpx.post(TOKEN_URL, data={
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "refresh_token": user["refresh_token"],
        "grant_type": "refresh_token",
    }))
    db.save_user(email, None, tokens["access_token"], time.time() + tokens["expires_in"])
    return tokens["access_token"]
