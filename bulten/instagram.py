"""Publish carousels and Reels with the Instagram API.

Works with both token kinds Meta hands out:
- system-user tokens from "API setup with Unified login" (start with "EAA", never expire) → graph.facebook.com,
  account id from the IG_USER_ID variable;
- Instagram Login tokens (start with "IG", 60 days, refreshable) → graph.instagram.com.
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path

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


def granted_permissions(token: str) -> list:
    """Permissions granted to a system-user token (no secret values)."""
    data = _call("GET", "me/permissions", token).get("data", [])
    return [p["permission"] for p in data if p.get("status") == "granted"]


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
        info = _call("GET", container_id, token, fields="status_code,status")
        status = info.get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise InstagramError(f"container {container_id} status {status}: {info.get('status', '')}")
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


def publish_reel(token: str, user_id: str, video_path, caption: str, trial: bool = False,
                 thumb_offset_ms: int | None = None) -> dict:
    """Upload an MP4 straight to Meta (resumable upload, no public hosting needed), then publish it as a Reels.

    trial=True posts a trial reel: shown to non-followers first, shared with followers automatically if it
    performs well. Returns {'id', 'permalink', 'trial'}.
    """
    params = {"media_type": "REELS", "upload_type": "resumable", "caption": caption}
    if thumb_offset_ms is not None:
        params["thumb_offset"] = str(int(thumb_offset_ms))
    if trial:
        params["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"})
    container = _call("POST", f"{user_id}/media", token, **params)
    cid = container["id"]
    uri = container.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{VERSION}/{cid}"
    data = Path(video_path).read_bytes()
    for attempt in range(3):
        try:
            r = requests.post(uri, data=data, timeout=600, headers={
                "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(data))})
        except requests.RequestException as exc:  # never print the request: its header carries the token
            if attempt < 2:
                time.sleep(15)
                continue
            raise InstagramError(f"reel upload: network error {type(exc).__name__}") from None
        if r.ok:
            break
        if r.status_code < 500 or attempt == 2:
            raise InstagramError(f"reel upload failed: HTTP {r.status_code} {r.text[:300]}")
        time.sleep(15)
    _wait_ready(token, cid, timeout=900)  # Meta transcodes the video first
    published = _call("POST", f"{user_id}/media_publish", token, creation_id=cid)
    info = {}
    try:
        info = _call("GET", published["id"], token, fields="permalink")
    except InstagramError as exc:
        print(f"[instagram] permalink lookup failed: {exc}")
    return {"id": published["id"], "permalink": info.get("permalink", ""), "trial": trial}


def profile_stats(token: str, user_id: str) -> dict:
    """Follower and post counts (for the connection check)."""
    return _call("GET", user_id, token, fields="followers_count,media_count")


def trial_reels_check(token: str, user_id: str) -> str:
    """'' if Instagram accepts a trial reel container for this account, else its refusal.

    Creates an empty resumable Reels container and never uploads or publishes it (it expires unused).
    """
    try:
        _call("POST", f"{user_id}/media", token, media_type="REELS", upload_type="resumable",
              trial_params=json.dumps({"graduation_strategy": "SS_PERFORMANCE"}))
        return ""
    except InstagramError as exc:
        return str(exc)


def refresh_token(token: str) -> dict:
    """Exchange a long-lived Instagram Login token (older than 24h) for a fresh 60-day one."""
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
    data = r.json() if r.content else {}
    if not r.ok or "access_token" not in data:
        raise InstagramError(f"token refresh failed: {data.get('error', {}).get('message', r.text[:200])}")
    return data
