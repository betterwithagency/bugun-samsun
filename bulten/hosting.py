"""Give the slides public URLs (Instagram fetches images by URL).

Images are force-pushed to a separate `media` branch of this (public) GitHub repo, so they never bloat the
main branch history, and are served from raw.githubusercontent.com pinned to that commit.
"""
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import requests


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def host_images(paths: list, folder: str) -> list:
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        raise RuntimeError("GITHUB_REPOSITORY / GITHUB_TOKEN missing (image hosting runs inside GitHub Actions)")
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / folder
        dest.mkdir(parents=True)
        for p in paths:
            shutil.copy(p, dest / Path(p).name)
        _git(tmp, "init", "-q", "-b", "media")
        _git(tmp, "config", "user.name", "samsun-bulten-bot")
        _git(tmp, "config", "user.email", "bot@users.noreply.github.com")
        _git(tmp, "add", ".")
        _git(tmp, "commit", "-q", "-m", f"media {folder}")
        try:
            _git(tmp, "push", "-q", "--force", f"https://x-access-token:{token}@github.com/{repo}.git", "media")
        except subprocess.CalledProcessError as exc:  # never print the URL: it carries the token
            raise RuntimeError(f"pushing images to the media branch failed: {exc.stderr.replace(token, '***')}") from None
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp, check=True, capture_output=True,
                             text=True).stdout.strip()
    urls = [f"https://raw.githubusercontent.com/{repo}/{sha}/{folder}/{Path(p).name}" for p in paths]
    deadline = time.time() + 180
    for url in urls:
        while True:
            r = requests.head(url, timeout=20)
            if r.status_code == 200:
                break
            if time.time() > deadline:
                raise RuntimeError(f"image not reachable: {url} ({r.status_code}); is the repository public?")
            time.sleep(5)
    return urls
