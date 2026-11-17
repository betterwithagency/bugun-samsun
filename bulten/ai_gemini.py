"""Gemini provider (Interactions API, google-genai SDK): Google Search grounding + URL context, JSON output."""
import copy
import json
import time

from .config import GEMINI_MODEL

_TOOLS = [{"type": "google_search"}, {"type": "url_context"}]


def _client():
    from google import genai  # reads GEMINI_API_KEY from the environment
    return genai.Client()


def _create(step: str, **body):
    """Run one interaction, retrying transient failures; return the completed Interaction."""
    client = _client()
    last = None
    for attempt in range(3):
        try:
            it = client.interactions.create(model=GEMINI_MODEL, **body)
        except Exception as exc:  # network / 5xx / quota: retry a few times with backoff
            last = exc
            print(f"[gemini] {step}: attempt {attempt + 1} failed: {exc}")
            time.sleep(20 * (attempt + 1))
            continue
        if it.status == "completed" and (it.output_text or "").strip():
            return it
        last = RuntimeError(f"{step}: status={it.status} errors={it.errors}")
        if it.status in ("failed", "incomplete") and attempt < 2:
            print(f"[gemini] {last}; retrying")
            time.sleep(10)
            continue
        break
    raise RuntimeError(f"gemini {step} failed: {last}")


def _sources(it) -> list:
    """URLs the model cited (url_citation annotations), for the research notes."""
    seen = []
    for step in it.steps or []:
        if getattr(step, "type", "") != "model_output":
            continue
        for block in getattr(step, "content", None) or []:
            for ann in getattr(block, "annotations", None) or []:
                if getattr(ann, "type", "") == "url_citation" and getattr(ann, "url", None):
                    item = f"- {getattr(ann, 'title', '') or ''} {ann.url}".strip()
                    if item not in seen:
                        seen.append(item)
    return seen


def _strip_unsupported(schema):
    """Gemini's schema subset: drop keywords it may reject; shapes are re-checked in code anyway."""
    s = copy.deepcopy(schema)

    def walk(node):
        if isinstance(node, dict):
            node.pop("additionalProperties", None)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(s)
    return s


def research(system: str, prompt: str) -> str:
    it = _create("research", input=prompt, system_instruction=system, tools=_TOOLS,
                 generation_config={"thinking_level": "high", "max_output_tokens": 32768})
    dossier = it.output_text.strip()
    cited = _sources(it)
    if cited:
        dossier += "\n\nAlıntılanan kaynak adresleri:\n" + "\n".join(cited[:40])
    return dossier


def write(system: str, task: str, schema: dict) -> dict:
    it = _create("write", input=task, system_instruction=system,
                 response_format={"type": "text", "mime_type": "application/json",
                                  "schema": _strip_unsupported(schema)},
                 generation_config={"thinking_level": "high", "max_output_tokens": 32768})
    return json.loads(it.output_text)


def check() -> str:
    """Free metadata call: confirms the key works and the model exists."""
    client = _client()  # keep a reference: a garbage-collected Client closes its HTTP session
    m = client.models.get(model=GEMINI_MODEL)
    return getattr(m, "name", GEMINI_MODEL)
