"""Keep the Instagram token alive: refresh it weekly and store the fresh one encrypted in data/.

The first token comes from the IG_ACCESS_TOKEN secret. Refreshed tokens are written to data/ig_token.enc,
encrypted with a key derived from the TOKEN_KEY secret, so the workflow can commit them safely.
If you later paste a new token into IG_ACCESS_TOKEN, it takes over automatically.
"""
import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken

from . import instagram
from .config import DATA

STORE = DATA / "ig_token.enc"
REFRESH_EVERY = timedelta(days=7)


def _fernet(secret: str) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def _seed(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:16]


def get_token() -> str:
    seed_token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    key = os.environ.get("TOKEN_KEY", "").strip()
    if not seed_token:
        raise RuntimeError("IG_ACCESS_TOKEN secret is missing")
    token, refreshed_at = seed_token, None
    if key and STORE.exists():
        try:
            stored = json.loads(_fernet(key).decrypt(STORE.read_bytes()))
            if stored.get("seed") == _seed(seed_token):
                token = stored["token"]
                refreshed_at = datetime.fromisoformat(stored["refreshed_at"])
        except (InvalidToken, ValueError, KeyError) as exc:
            print(f"[tokens] stored token unreadable, using the secret: {exc}")
    now = datetime.now(timezone.utc)
    if refreshed_at is None or now - refreshed_at > REFRESH_EVERY:
        try:
            token = instagram.refresh_token(token)["access_token"]
            refreshed_at = now
            print("[tokens] Instagram token refreshed")
        except instagram.InstagramError as exc:
            print(f"[tokens] refresh skipped: {exc}")
        if key and refreshed_at:
            payload = {"token": token, "refreshed_at": refreshed_at.isoformat(), "seed": _seed(seed_token)}
            STORE.parent.mkdir(parents=True, exist_ok=True)
            STORE.write_bytes(_fernet(key).encrypt(json.dumps(payload).encode()))
        elif not key:
            print("[tokens] TOKEN_KEY not set: refreshed token is not stored and will expire in 60 days")
    return token
