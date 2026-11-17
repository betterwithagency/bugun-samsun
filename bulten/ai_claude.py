"""Claude provider (Anthropic SDK): web search + web fetch, then structured JSON output."""
import json

from .config import MODEL

FALLBACK_BETA = "server-side-fallback-2026-07-01"


def _client():
    import anthropic
    return anthropic.Anthropic(max_retries=4)


def _text(msg) -> str:
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def _check_stop(msg, step: str):
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"{step}: model declined the request ({getattr(msg, 'stop_details', None)})")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError(f"{step}: output hit max_tokens")


def research(system: str, prompt: str) -> str:
    client = _client()
    tools = [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": 12,
         "user_location": {"type": "approximate", "city": "Samsun", "country": "TR", "timezone": "Europe/Istanbul"}},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 15},
    ]
    messages = [{"role": "user", "content": prompt}]
    responses = []
    for _ in range(8):  # server tools may pause a long turn; resume by appending the assistant content
        with client.beta.messages.stream(
            model=MODEL, max_tokens=64000, betas=[FALLBACK_BETA], fallbacks="default",
            cache_control={"type": "ephemeral"}, system=system, messages=messages, tools=tools,
            output_config={"effort": "high"},
        ) as stream:
            msg = stream.get_final_message()
        responses.append(msg)
        if msg.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": msg.content})
            continue
        _check_stop(msg, "research")
        dossier = _text(msg) or "\n".join(_text(m) for m in responses)
        if not dossier:
            raise RuntimeError("research: empty dossier")
        return dossier
    raise RuntimeError("research: too many pause_turn continuations")


def write(system: str, task: str, schema: dict) -> dict:
    client = _client()
    with client.beta.messages.stream(
        model=MODEL, max_tokens=32000, betas=[FALLBACK_BETA], fallbacks="default", system=system,
        messages=[{"role": "user", "content": task}],
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
    ) as stream:
        msg = stream.get_final_message()
    _check_stop(msg, "write")
    return json.loads(_text(msg))


def check() -> str:
    return _client().models.retrieve(MODEL).id  # free metadata call
