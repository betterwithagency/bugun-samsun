"""Render sample bulletins: python render_samples.py <theme> [edition ...]"""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
from bulten import weather  # noqa: E402
from bulten.render import render  # noqa: E402

theme, _, fontset = sys.argv[1].partition(":")
fontset = fontset or "libron"
editions = sys.argv[2:] or ["gundem2"]
w = weather.today()
for name in editions:
    issue = json.loads(Path(f"samples/{name}.json").read_text(encoding="utf-8"))
    issue["weather"] = w
    paths = render(issue, Path(f"output/samples/{theme}-{fontset}/{name}"), theme=theme, sample=True, strict=False, fontset=fontset)
    print(theme, name, len(paths), "slides")
