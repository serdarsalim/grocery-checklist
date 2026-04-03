#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request


CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
WRAPPER_PATH = Path.home() / ".openclaw" / "workspace" / "grocery.sh"
BOT_STATE_PATH = Path.home() / ".openclaw" / "data" / "grocery-checklist" / "telegram-bot-state.json"


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def grocery_account_config() -> dict[str, Any]:
    config = load_config()
    return (((config.get("channels") or {}).get("telegram") or {}).get("accounts") or {}).get("grocery") or {}


def telegram_token() -> str:
    token = grocery_account_config().get("botToken")
    if not token:
        raise SystemExit("Missing grocery Telegram bot token in openclaw.json")
    return token


def allowed_user_ids() -> set[str]:
    allow_from = grocery_account_config().get("allowFrom") or []
    return {str(value) for value in allow_from}


def api(method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    token = telegram_token()
    payload = payload or {}
    data = parse.urlencode({
        key: json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        for key, value in payload.items()
    }).encode("utf-8")
    req = request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data, method="POST")
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(detail or str(exc)) from exc
    decoded = json.loads(raw)
    if not decoded.get("ok"):
        raise RuntimeError(decoded.get("description", f"Telegram API error for {method}"))
    return decoded


def run_wrapper(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [str(WRAPPER_PATH), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "grocery wrapper failed").strip())
    stdout = completed.stdout.strip()
    if not stdout:
        return {"ok": True}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"ok": True, "raw": stdout}


def send_text(chat_id: str, text: str) -> None:
    api("sendMessage", {"chat_id": chat_id, "text": text})


def answer_callback(callback_id: str) -> None:
    api("answerCallbackQuery", {"callback_query_id": callback_id})


def load_offset() -> int | None:
    if not BOT_STATE_PATH.exists():
        return None
    try:
        data = json.loads(BOT_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    value = data.get("offset")
    return int(value) if isinstance(value, int) else None


def save_offset(offset: int) -> None:
    BOT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOT_STATE_PATH.write_text(json.dumps({"offset": offset}, indent=2) + "\n", encoding="utf-8")


def split_items(raw: str) -> list[str]:
    parts = re.split(r",|\n|(?:\band\b)", raw, flags=re.IGNORECASE)
    items = []
    for part in parts:
        cleaned = re.sub(r"\s+", " ", part).strip(" .")
        if cleaned:
            items.append(cleaned)
    return items


def parse_merge_intent(text: str) -> tuple[str, list[str]] | None:
    lower = text.lower().strip()
    match = re.search(r"merge\s+(.+?)\s+into\s+(.+)$", lower)
    if match:
        sources = split_items(match.group(1))
        destination = re.sub(r"\s+", " ", match.group(2)).strip()
        if destination and sources:
            return destination, sources

    match = re.search(r"fix\s+(.+)$", lower)
    if match:
        destination = re.sub(r"\s+", " ", match.group(1)).strip()
        tokens = destination.split()
        if len(tokens) >= 2:
            return destination, tokens

    match = re.search(r"(.+?)\s+shouldn['’]t be separate", lower)
    if match:
        source = re.sub(r"\s+", " ", match.group(1)).strip()
        if " and " in source:
            sources = [part.strip() for part in source.split(" and ") if part.strip()]
            destination = " ".join(sources)
            if len(sources) >= 2:
                return destination, sources
    return None


def parse_rename_intent(text: str) -> tuple[str, str] | None:
    lower = text.lower().strip()
    match = re.search(r"rename\s+(.+?)\s+to\s+(.+)$", lower)
    if match:
        source = re.sub(r"\s+", " ", match.group(1)).strip()
        destination = re.sub(r"\s+", " ", match.group(2)).strip()
        if source and destination:
            return source, destination
    match = re.search(r"change\s+(.+?)\s+to\s+(.+)$", lower)
    if match:
        source = re.sub(r"\s+", " ", match.group(1)).strip()
        destination = re.sub(r"\s+", " ", match.group(2)).strip()
        if source and destination:
            return source, destination
    return None


def is_shopping_view_intent(lower: str) -> bool:
    if "shopping view" in lower or "shopping list" in lower:
        return True
    if "need to buy" in lower:
        return True
    if "i'm shopping" in lower or "im shopping" in lower:
        return True
    return False


def is_pantry_view_intent(lower: str) -> bool:
    if "show pantry" in lower or "show me the pantry" in lower or "pantry view" in lower:
        return True
    if "what do i have" in lower or "what's in the pantry" in lower or "whats in the pantry" in lower:
        return True
    return False


def is_greeting(lower: str) -> bool:
    greetings = {"hi", "hello", "hey", "yo", "sup", "are you there", "hello?", "hi?"}
    return lower in greetings


def handle_text(chat_id: str, sender_id: str, text: str) -> None:
    lower = text.lower().strip()

    if is_shopping_view_intent(lower):
        run_wrapper(["render-telegram", "--target", sender_id, "--account", "grocery"])
        return

    if is_pantry_view_intent(lower):
        run_wrapper(["render-telegram", "--target", sender_id, "--account", "grocery", "--mode", "all"])
        return

    if is_greeting(lower):
        send_text(chat_id, "I'm here.")
        return

    rename = parse_rename_intent(text)
    if rename:
        source, destination = rename
        run_wrapper(["rename", source, destination])
        send_text(chat_id, f"Renamed to {destination}.")
        return

    merge = parse_merge_intent(text)
    if merge:
        destination, sources = merge
        run_wrapper(["merge", destination, *sources])
        send_text(chat_id, f"Merged into {destination}.")
        return

    if any(phrase in lower for phrase in ["ran out", "need ", "add to groceries", "add ", "we also need"]):
        payload = text
        payload = re.sub(r"^(we also need|i need|we need|add to groceries|add)\s+", "", payload, flags=re.IGNORECASE)
        payload = re.sub(r"^(i ran out of|we ran out of)\s+", "", payload, flags=re.IGNORECASE)
        items = split_items(payload)
        if items:
            run_wrapper(["need", *items])
            send_text(chat_id, "Added to groceries.")
            return

    if any(phrase in lower for phrase in ["i bought", "we bought", "got ", "picked up", "mark bought"]):
        payload = text
        payload = re.sub(r"^(i bought|we bought|got|picked up|mark bought)\s+", "", payload, flags=re.IGNORECASE)
        items = split_items(payload)
        if items:
            run_wrapper(["have", *items])
            send_text(chat_id, "Updated pantry.")
            return

    send_text(chat_id, "Tell me what grocery action you want.")


def handle_callback(callback: dict[str, Any]) -> None:
    callback_id = callback.get("id")
    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id"))
    from_user = callback.get("from") or {}
    sender_id = str(from_user.get("id"))
    data = callback.get("data") or ""
    if data.startswith("gchk:"):
        run_wrapper(["handle-callback", data, "--target", sender_id, "--account", "grocery"])
    if callback_id:
        answer_callback(callback_id)


def poll_forever() -> None:
    allow = allowed_user_ids()
    offset = load_offset()
    while True:
        payload: dict[str, Any] = {"timeout": 25}
        if offset is not None:
            payload["offset"] = offset
        updates = api("getUpdates", payload).get("result", [])
        for update in updates:
            offset = int(update["update_id"]) + 1
            if "callback_query" in update:
                callback = update["callback_query"]
                sender_id = str((callback.get("from") or {}).get("id"))
                if sender_id in allow:
                    handle_callback(callback)
                continue

            message = update.get("message") or {}
            chat = message.get("chat") or {}
            if chat.get("type") != "private":
                continue
            sender_id = str((message.get("from") or {}).get("id"))
            if sender_id not in allow:
                continue
            text = message.get("text")
            if isinstance(text, str) and text.strip():
                handle_text(str(chat.get("id")), sender_id, text)
        if offset is not None:
            save_offset(offset)
        time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    poll_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
