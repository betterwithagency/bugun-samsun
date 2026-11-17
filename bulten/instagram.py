"""Publish a carousel with the Instagram API (Instagram Login, graph.instagram.com)."""
import os
import time

import requests

HOST = "https://graph.instagram.com"
VERSION = os.environ.get("IG_API_VERSION", "v24.0")
_TRANSIENT_CODES = {1, 2, 4, 17, 32, 341, 613}


class InstagramError(RuntimeError):
    pass


def _call(method: str, path: str, token: str, **params) -> dict:
    url = f"{HOST}/{VERSION}/{path}"
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


def me(token: str) -> dict:
    """{'user_id': ..., 'username': ...} of the account the token belongs to."""
    return _call("GET", "me", token, fields="user_id,username")


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
    """Exchange a long-lived token (older than 24h) for a fresh 60-day one."""
    r = requests.get(f"{HOST}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
    data = r.json() if r.content else {}
    if not r.ok or "access_token" not in data:
        raise InstagramError(f"token refresh failed: {data.get('error', {}).get('message', r.text[:200])}")
    return data
