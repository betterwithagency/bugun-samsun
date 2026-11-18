"""Publish a carousel with the Instagram API.

Works with both token kinds Meta hands out:
- system-user tokens from "API setup with Unified login" (start with "EAA", never expire) → graph.facebook.com,
  account id from the IG_USER_ID variable;
- Instagram Login tokens (start with "IG", 60 days, refreshable) → graph.instagram.com.
"""
import os
import time
from datetime import datetime

import requests

VERSION = os.environ.get("IG_API_VERSION") or "v24.0"
_TRANSIENT_CODES = {1, 2, 4, 17, 32, 341, 613}


class InstagramError(RuntimeError):
    pass


def is_system_user_token(token: str) -> bool:
    return token.startswith("EAA")


def _host(token: str) -> str:
    return "https://graph.facebook.com" if is_system_user_token(token) else "https://graph.instagram.com"


def _call(method: str, path: str, token: str, **params) -> dict:
    url = f"{_host(token)}/{VERSION}/{path}"
    payload = {**params, "access_token": token}
    for attempt in range(4):
        try:
            if method == "GET":
                r = requests.get(url, params=payload, timeout=60)
            else:
                r = requests.post(url, data=payload, timeout=120)
        except requests.RequestException as exc:
            if attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            raise InstagramError(f"{path}: network error {exc}") from exc
        try:
            data = r.json()
        except ValueError:
            data = {}
        if r.ok and "error" not in data:
            return data
        err = data.get("error", {})
        transient = err.get("is_transient") or r.status_code >= 500 or err.get("code") in _TRANSIENT_CODES
        if transient and attempt < 3:
            print(f"[instagram] {path}: transient error, retrying ({err.get('message')})")
            time.sleep(15 * (attempt + 1))
            continue
        raise InstagramError(f"{path}: {err.get('message', r.text[:200])} "
                             f"(code {err.get('code')}, subcode {err.get('error_subcode')})")
    raise InstagramError(f"{path}: gave up after retries")


def account(token: str) -> dict:
    """{'user_id': ..., 'username': ...} of the Instagram account we publish to."""
    user_id = (os.environ.get("IG_USER_ID") or "").strip()
    if user_id:
        info = _call("GET", user_id, token, fields="username")
        return {"user_id": user_id, "username": info.get("username", "")}
    if is_system_user_token(token):
        raise InstagramError("IG_USER_ID variable is required with a system-user token")
    return _call("GET", "me", token, fields="user_id,username")


def token_info(token: str) -> dict:
    """Granted scopes and type of a system-user token (debug_token); no secret values."""
    data = _call("GET", "debug_token", token, input_token=token).get("data", {})
    return {"type": data.get("type"), "app_id": data.get("app_id"), "valid": data.get("is_valid"),
            "scopes": data.get("scopes", []),
            "granular": {g.get("scope"): g.get("target_ids", []) for g in data.get("granular_scopes", [])}}


def posted_since(token: str, user_id: str, marker: str, since: datetime) -> str:
    """Permalink of a post made at/after `since` whose caption contains `marker`, or ''."""
    data = _call("GET", f"{user_id}/media", token, fields="caption,timestamp,permalink", limit=12)
    for m in data.get("data", []):
        try:
            ts = datetime.strptime(m.get("timestamp", ""), "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            continue
        if ts >= since and marker in (m.get("caption") or ""):
            return m.get("permalink") or m.get("id", "?")
    return ""


def _wait_ready(token: str, container_id: str, timeout: int = 300):
    deadline = time.time() + timeout
    while True:
        status = _call("GET", container_id, token, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise InstagramError(f"container {container_id} status {status}")
        if time.time() > deadline:
            raise InstagramError(f"container {container_id} not ready after {timeout}s (last: {status})")
        time.sleep(5)


def publish_carousel(token: str, user_id: str, image_urls: list, caption: str) -> dict:
    """Create one container per JPEG, a carousel container, then publish. Returns {'id', 'permalink'}."""
    if not 2 <= len(image_urls) <= 20:
        raise InstagramError(f"carousel needs 2-20 images, got {len(image_urls)}")
    children = []
    for url in image_urls:
        c = _call("POST", f"{user_id}/media", token, image_url=url, is_carousel_item="true")
        children.append(c["id"])
    for cid in children:
        _wait_ready(token, cid)
    parent = _call("POST", f"{user_id}/media", token, media_type="CAROUSEL",
                   children=",".join(children), caption=caption)
    _wait_ready(token, parent["id"])
    published = _call("POST", f"{user_id}/media_publish", token, creation_id=parent["id"])
    info = {}
    try:
        info = _call("GET", published["id"], token, fields="permalink")
    except InstagramError as exc:  # the post is live; a missing permalink is not a failure
        print(f"[instagram] permalink lookup failed: {exc}")
    return {"id": published["id"], "permalink": info.get("permalink", "")}


def refresh_token(token: str) -> dict:
    """Exchange a long-lived Instagram Login token (older than 24h) for a fresh 60-day one."""
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
    data = r.json() if r.content else {}
    if not r.ok or "access_token" not in data:
        raise InstagramError(f"token refresh failed: {data.get('error', {}).get('message', r.text[:200])}")
    return data
