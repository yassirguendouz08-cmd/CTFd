"""Request-local challenge translations; never modify competition records.

The board opts in with localized=1. Administrative APIs keep their editable
source text. Catalogues contain public teaching text only, never flag answers.
"""
import json
from functools import lru_cache
from pathlib import Path

from flask import request

from CTFd.utils.config.pages import build_markdown
from CTFd.utils.user import get_locale


@lru_cache(maxsize=1)
def catalog():
    return json.loads(Path(__file__).with_name("bootcamp.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def ui_catalog():
    return json.loads(Path(__file__).with_name("ui.json").read_text(encoding="utf-8"))


def locale():
    return str(get_locale() or "en").replace("_", "-").split("-")[0]


def messages():
    return ui_catalog().get(locale(), {})


def copy(text):
    return messages().get(text, text)


def entry(challenge):
    if request.args.get("localized") != "1":
        return None
    for tag in challenge.tags:
        value = tag["value"] if isinstance(tag, dict) else tag.value
        if value.startswith("bootcamp-first-steps:"):
            return catalog().get(value.split(":", 1)[1])
    return None


def translated_field(item, field, source):
    # An organizer's subsequent edits take precedence over a stale translation.
    if source != item["fr"][field]:
        return source
    return item.get(locale(), item["en"])[field]


def localize_challenge(data, challenge):
    item = entry(challenge)
    if not item:
        return data
    result = dict(data)
    for field in ("name", "description"):
        if field in result:
            result[field] = translated_field(item, field, result[field])
    if "category" in result:
        result["category"] = copy(result["category"])
    if "tags" in result:
        result["tags"] = [
            {**tag, "value": copy(tag["value"])} if isinstance(tag, dict) else copy(tag)
            for tag in result["tags"]
            if not (tag["value"] if isinstance(tag, dict) else tag).startswith("bootcamp-first-steps:")
        ]
    return result


def localize_hint(data, hint):
    item = entry(hint.challenge)
    if not item or hint.content not in item["fr"]["hints"]:
        return data
    index = item["fr"]["hints"].index(hint.content)
    result = dict(data)
    if result.get("title") == f"Indice {index + 1}":
        result["title"] = f"{copy('Hint')} {index + 1}"
    # Keep locked hints locked: translate only fields already authorized upstream.
    if "content" in result:
        result["content"] = item.get(locale(), item["en"])["hints"][index]
        if "html" in result:
            result["html"] = build_markdown(result["content"])
    return result


class ChallengeView:
    """Render translated fields without dirtying a SQLAlchemy or cached object."""

    def __init__(self, challenge, data):
        self._challenge = challenge
        self._data = data

    def __getattr__(self, name):
        if name in ("name", "category", "description"):
            return self._data[name]
        if name == "html":
            from CTFd.utils.helpers import markup
            return markup(build_markdown(self._data["description"]))
        return getattr(self._challenge, name)
