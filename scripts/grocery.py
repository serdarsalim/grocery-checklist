#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


STATUS_NEEDED = "needed"
STATUS_HAVE = "have"
DEFAULT_ACCOUNT = "default"
CALLBACK_PREFIX = "gchk"
CALLBACK_TOGGLE = "tgl"
CALLBACK_DONE = "done"
CALLBACK_CLEAR = "clear"
CALLBACK_VIEW = "view"
VIEW_NEEDED = "needed"
VIEW_ALL = "all"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def state_path() -> Path:
    raw = os.environ.get("GROCERY_STATE_FILE")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".openclaw" / "data" / "grocery-checklist" / "state.json"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": 1,
            "updated_at": utc_now(),
            "items": {},
            "views": {},
        }
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SystemExit("State file is invalid.")
    data.setdefault("version", 1)
    data.setdefault("updated_at", utc_now())
    data.setdefault("items", {})
    data.setdefault("views", {})
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    ensure_parent(path)
    state["updated_at"] = utc_now()
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")
    tmp.replace(path)


def normalize_name(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[&+]", " and ", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def display_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    return value


def item_id_for(normalized: str) -> str:
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]


def split_item_tokens(values: list[str]) -> list[str]:
    items: list[str] = []
    for raw in values:
        for part in re.split(r",|\n|(?:\band\b)", raw):
            cleaned = display_name(part)
            if cleaned:
                items.append(cleaned)
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        key = normalize_name(item)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def get_or_create_item(state: dict[str, Any], raw_name: str) -> dict[str, Any]:
    name = display_name(raw_name)
    normalized = normalize_name(name)
    if not normalized:
        raise ValueError("Empty grocery item.")
    item_id = item_id_for(normalized)
    items = state["items"]
    existing = items.get(item_id)
    if existing:
        existing["normalized"] = normalized
        existing.setdefault("created_at", utc_now())
        return existing
    item = {
        "id": item_id,
        "name": name,
        "normalized": normalized,
        "status": STATUS_NEEDED,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    items[item_id] = item
    return item


def update_status(state: dict[str, Any], raw_items: list[str], status: str) -> list[dict[str, Any]]:
    changed: list[dict[str, Any]] = []
    for raw_name in split_item_tokens(raw_items):
        item = get_or_create_item(state, raw_name)
        if not item.get("name"):
            item["name"] = display_name(raw_name)
        item["status"] = status
        item["updated_at"] = utc_now()
        changed.append(item)
    return changed


def remove_items(state: dict[str, Any], raw_items: list[str]) -> list[str]:
    removed: list[str] = []
    for raw_name in split_item_tokens(raw_items):
        normalized = normalize_name(raw_name)
        item_id = item_id_for(normalized)
        item = state["items"].pop(item_id, None)
        if item:
            removed.append(item["name"])
    return removed


def sorted_items(state: dict[str, Any], status: str | None = None) -> list[dict[str, Any]]:
    items = list(state["items"].values())
    if status in {STATUS_NEEDED, STATUS_HAVE}:
        items = [item for item in items if item.get("status") == status]
    return sorted(items, key=lambda item: (item.get("status") != STATUS_NEEDED, item.get("name", "").lower()))


def sender_key(account: str, target: str, thread_id: str | None) -> str:
    return f"{account}:{target}:{thread_id or '-'}"


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def checkbox_line(name: str, checked: bool) -> str:
    safe = html_escape(name)
    if checked:
        return f"☑ <s>{safe}</s>"
    return f"☐ {safe}"


def resolve_view(state: dict[str, Any], account: str, target: str, thread_id: str | None) -> dict[str, Any]:
    key = sender_key(account, target, thread_id)
    views = state["views"]
    raw = views.get(key)
    if isinstance(raw, dict):
        raw.setdefault("pending_ids", [])
        raw.setdefault("mode", VIEW_NEEDED)
        raw.setdefault("account", account)
        raw.setdefault("target", target)
        raw.setdefault("thread_id", thread_id)
        return raw
    view = {
        "account": account,
        "target": target,
        "thread_id": thread_id,
        "mode": VIEW_NEEDED,
        "pending_ids": [],
        "updated_at": utc_now(),
    }
    views[key] = view
    return view


def render_message(state: dict[str, Any], mode: str = VIEW_NEEDED, pending_ids: set[str] | None = None, committed: bool = False) -> dict[str, Any]:
    needed = sorted_items(state, STATUS_NEEDED)
    have = sorted_items(state, STATUS_HAVE)
    body: list[str] = []
    buttons: list[list[dict[str, str]]] = []
    pending_ids = pending_ids or set()

    if mode == VIEW_ALL:
        body.append("Pantry")
        body.append("")
        body.append("Need to buy:")
        if needed:
            for idx, item in enumerate(needed, 1):
                body.append(f"{idx}. {item['name']}")
        else:
            body.append("Nothing pending.")
        body.append("")
        body.append("In stock:")
        if have:
            for item in have:
                body.append(f"- {item['name']}")
        else:
            body.append("Nothing marked as in stock yet.")
        buttons.append([{"text": "Shopping View", "callback_data": f"{CALLBACK_PREFIX}:{CALLBACK_VIEW}:{VIEW_NEEDED}"}])
    else:
        if committed:
            body.append("Updated your pantry.")
            body.append("")
        body.append("Groceries to buy")
        body.append("")
        if needed:
            for item in needed:
                body.append(checkbox_line(item["name"], item["id"] in pending_ids))
        else:
            body.append("Nothing pending.")
        body.append("")
        body.append("Tap items to check them, then tap Done.")

        row: list[dict[str, str]] = []
        for item in needed:
            checked = item["id"] in pending_ids
            row.append({
                "text": f"{'☑' if checked else '☐'} {item['name']}",
                "callback_data": f"{CALLBACK_PREFIX}:{CALLBACK_TOGGLE}:{item['id']}",
            })
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        footer_row = [
            {"text": "Done", "callback_data": f"{CALLBACK_PREFIX}:{CALLBACK_DONE}:needed"},
            {"text": "Clear", "callback_data": f"{CALLBACK_PREFIX}:{CALLBACK_CLEAR}:needed"},
        ]
        buttons.append(footer_row)
        buttons.append([{"text": "Pantry View", "callback_data": f"{CALLBACK_PREFIX}:{CALLBACK_VIEW}:{VIEW_ALL}"}])
    return {
        "message": "\n".join(body).strip(),
        "buttons": buttons,
    }


def run_openclaw(args: list[str], dry_run: bool = False) -> dict[str, Any]:
    cmd = ["openclaw", *args]
    if dry_run:
        return {"ok": True, "dry_run": True, "command": cmd}
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "openclaw command failed").strip())
    stdout = completed.stdout.strip()
    if not stdout:
        return {"ok": True}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"ok": True, "raw": stdout}


def openclaw_config_path() -> Path:
    return Path.home() / ".openclaw" / "openclaw.json"


def resolve_telegram_token(account: str) -> str:
    config = json.loads(openclaw_config_path().read_text(encoding="utf-8"))
    token = (((config.get("channels") or {}).get("telegram") or {}).get("accounts") or {}).get(account, {}).get("botToken")
    if not token:
        raise RuntimeError(f"Missing Telegram bot token for account {account}.")
    return token


def telegram_api(method: str, payload: dict[str, Any], account: str, dry_run: bool = False) -> dict[str, Any]:
    token = resolve_telegram_token(account)
    if dry_run:
        return {"ok": True, "dry_run": True, "method": method, "payload": payload}
    data = parse.urlencode({k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in payload.items()}).encode("utf-8")
    req = request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data, method="POST")
    try:
        with request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(detail or str(exc)) from exc
    decoded = json.loads(raw)
    if not decoded.get("ok"):
        raise RuntimeError(decoded.get("description", "Telegram API call failed."))
    return decoded


def telegram_send_message(target: str, account: str, text: str, buttons: list[list[dict[str, str]]], thread_id: str | None, dry_run: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "chat_id": target,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": buttons},
    }
    if thread_id:
        payload["message_thread_id"] = thread_id
    return telegram_api("sendMessage", payload, account, dry_run=dry_run)


def telegram_edit_message(view: dict[str, Any], account: str, text: str, buttons: list[list[dict[str, str]]], dry_run: bool) -> dict[str, Any]:
    if not view.get("message_id") or not view.get("chat_id"):
        raise RuntimeError("No Telegram checklist message to edit.")
    payload = {
        "chat_id": view["chat_id"],
        "message_id": view["message_id"],
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": buttons},
    }
    return telegram_api("editMessageText", payload, account, dry_run=dry_run)


def telegram_delete_message(view: dict[str, Any], account: str, dry_run: bool) -> None:
    if not view.get("message_id") or not view.get("chat_id"):
        return
    try:
        telegram_api("deleteMessage", {
            "chat_id": view["chat_id"],
            "message_id": view["message_id"],
        }, account, dry_run=dry_run)
    except RuntimeError:
        return


def maybe_delete_previous_view(state: dict[str, Any], key: str, account: str, dry_run: bool) -> None:
    view = state["views"].get(key)
    if isinstance(view, dict):
        telegram_delete_message(view, account, dry_run=dry_run)


def send_telegram_view(state: dict[str, Any], target: str, account: str, mode: str, thread_id: str | None, dry_run: bool) -> dict[str, Any]:
    view = resolve_view(state, account, target, thread_id)
    if mode != VIEW_NEEDED:
        view["pending_ids"] = []
    view["mode"] = mode
    pending_ids = set(view.get("pending_ids", []))
    payload = render_message(state, mode=mode, pending_ids=pending_ids)
    key = sender_key(account, target, thread_id)
    if not dry_run:
        maybe_delete_previous_view(state, key, account, dry_run=False)
    result = telegram_send_message(target, account, payload["message"], payload["buttons"], thread_id, dry_run=dry_run)
    message_obj = result.get("result", {})
    view.update({
        "message_id": message_obj.get("message_id"),
        "chat_id": (message_obj.get("chat") or {}).get("id", target),
        "updated_at": utc_now(),
    })
    return {
        "ok": True,
        "view": view,
        "message": payload["message"],
        "buttons": payload["buttons"],
        "result": result,
    }


def parse_callback(raw: str) -> tuple[str, str] | None:
    match = re.search(r"(?:callback_data:\s*)?(gchk:[^\s]+)", raw)
    token = match.group(1).strip() if match else raw.strip()
    parts = token.split(":")
    if len(parts) != 3 or parts[0] != CALLBACK_PREFIX:
        return None
    return parts[1], parts[2]


def edit_existing_view(state: dict[str, Any], target: str, account: str, thread_id: str | None, mode: str, dry_run: bool, committed: bool = False) -> dict[str, Any]:
    view = resolve_view(state, account, target, thread_id)
    pending_ids = set(view.get("pending_ids", []))
    payload = render_message(state, mode=mode, pending_ids=pending_ids, committed=committed)
    result = telegram_edit_message(view, account, payload["message"], payload["buttons"], dry_run=dry_run)
    view["mode"] = mode
    view["updated_at"] = utc_now()
    return {
        "ok": True,
        "view": view,
        "message": payload["message"],
        "buttons": payload["buttons"],
        "result": result,
    }


def handle_callback(state: dict[str, Any], callback: str, target: str, account: str, thread_id: str | None, dry_run: bool) -> dict[str, Any]:
    parsed = parse_callback(callback)
    if not parsed:
        raise RuntimeError("Unsupported callback payload.")
    action, value = parsed
    view = resolve_view(state, account, target, thread_id)
    pending_ids = set(view.get("pending_ids", []))
    if action == CALLBACK_TOGGLE:
        if value in pending_ids:
            pending_ids.remove(value)
        else:
            pending_ids.add(value)
        view["pending_ids"] = sorted(pending_ids)
        return edit_existing_view(state, target=target, account=account, thread_id=thread_id, mode=VIEW_NEEDED, dry_run=dry_run)
    if action == CALLBACK_DONE:
        return commit_pending(state, target=target, account=account, thread_id=thread_id, dry_run=dry_run)
    if action == CALLBACK_CLEAR:
        return clear_pending(state, target=target, account=account, thread_id=thread_id, dry_run=dry_run)
    if action == CALLBACK_VIEW:
        mode = VIEW_ALL if value == VIEW_ALL else VIEW_NEEDED
        if view.get("message_id"):
            if mode != VIEW_NEEDED:
                view["pending_ids"] = []
            return edit_existing_view(state, target=target, account=account, thread_id=thread_id, mode=mode, dry_run=dry_run)
        return send_telegram_view(state, target=target, account=account, mode=mode, thread_id=thread_id, dry_run=dry_run)
    raise RuntimeError("Unsupported callback action.")


def toggle_pending(state: dict[str, Any], item_id: str, target: str, account: str, thread_id: str | None, dry_run: bool) -> dict[str, Any]:
    view = resolve_view(state, account, target, thread_id)
    pending_ids = set(view.get("pending_ids", []))
    if item_id in pending_ids:
        pending_ids.remove(item_id)
    else:
        if item_id not in state["items"]:
            raise RuntimeError("Grocery item not found.")
        pending_ids.add(item_id)
    view["pending_ids"] = sorted(pending_ids)
    return edit_existing_view(state, target=target, account=account, thread_id=thread_id, mode=VIEW_NEEDED, dry_run=dry_run)


def commit_pending(state: dict[str, Any], target: str, account: str, thread_id: str | None, dry_run: bool) -> dict[str, Any]:
    view = resolve_view(state, account, target, thread_id)
    pending_ids = set(view.get("pending_ids", []))
    for item_id in list(pending_ids):
        item = state["items"].get(item_id)
        if item:
            item["status"] = STATUS_HAVE
            item["updated_at"] = utc_now()
    view["pending_ids"] = []
    return edit_existing_view(state, target=target, account=account, thread_id=thread_id, mode=VIEW_NEEDED, dry_run=dry_run, committed=True)


def clear_pending(state: dict[str, Any], target: str, account: str, thread_id: str | None, dry_run: bool) -> dict[str, Any]:
    view = resolve_view(state, account, target, thread_id)
    view["pending_ids"] = []
    return edit_existing_view(state, target=target, account=account, thread_id=thread_id, mode=VIEW_NEEDED, dry_run=dry_run)


def print_json(data: dict[str, Any]) -> None:
    json.dump(data, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pantry-backed grocery checklist for OpenClaw and Telegram.")
    parser.add_argument("--state-file", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, status in [("need", STATUS_NEEDED), ("out", STATUS_NEEDED), ("have", STATUS_HAVE), ("buy", STATUS_HAVE)]:
        cmd = sub.add_parser(name)
        cmd.add_argument("items", nargs="+")
        cmd.set_defaults(status=status)

    remove = sub.add_parser("remove")
    remove.add_argument("items", nargs="+")

    show = sub.add_parser("show")
    show.add_argument("--mode", choices=[VIEW_NEEDED, VIEW_ALL], default=VIEW_NEEDED)
    show.add_argument("--json", action="store_true")

    ls = sub.add_parser("list")
    ls.add_argument("--status", choices=[STATUS_NEEDED, STATUS_HAVE, "all"], default="all")
    ls.add_argument("--json", action="store_true")

    render = sub.add_parser("render-telegram")
    render.add_argument("--target", required=True)
    render.add_argument("--account", default=DEFAULT_ACCOUNT)
    render.add_argument("--mode", choices=[VIEW_NEEDED, VIEW_ALL], default=VIEW_NEEDED)
    render.add_argument("--thread-id")
    render.add_argument("--dry-run", action="store_true")

    callback = sub.add_parser("handle-callback")
    callback.add_argument("callback")
    callback.add_argument("--target", required=True)
    callback.add_argument("--account", default=DEFAULT_ACCOUNT)
    callback.add_argument("--thread-id")
    callback.add_argument("--dry-run", action="store_true")

    toggle = sub.add_parser("toggle")
    toggle.add_argument("item_id")
    toggle.add_argument("--target", required=True)
    toggle.add_argument("--account", default=DEFAULT_ACCOUNT)
    toggle.add_argument("--thread-id")
    toggle.add_argument("--dry-run", action="store_true")

    done = sub.add_parser("done")
    done.add_argument("--target", required=True)
    done.add_argument("--account", default=DEFAULT_ACCOUNT)
    done.add_argument("--thread-id")
    done.add_argument("--dry-run", action="store_true")

    clear = sub.add_parser("clear-selection")
    clear.add_argument("--target", required=True)
    clear.add_argument("--account", default=DEFAULT_ACCOUNT)
    clear.add_argument("--thread-id")
    clear.add_argument("--dry-run", action="store_true")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.state_file).expanduser() if args.state_file else state_path()
    state = load_state(path)
    changed = False

    if args.command in {"need", "out", "have", "buy"}:
        items = update_status(state, args.items, args.status)
        changed = True
        save_state(path, state)
        print_json({
            "ok": True,
            "updated": [{"id": item["id"], "name": item["name"], "status": item["status"]} for item in items],
            "state_file": str(path),
        })
        return

    if args.command == "remove":
        removed = remove_items(state, args.items)
        changed = True
        save_state(path, state)
        print_json({"ok": True, "removed": removed, "state_file": str(path)})
        return

    if args.command == "show":
        payload = render_message(state, mode=args.mode)
        data = {"ok": True, "message": payload["message"], "buttons": payload["buttons"]}
        if args.json:
            print_json(data)
        else:
            print(payload["message"])
        return

    if args.command == "list":
        status = None if args.status == "all" else args.status
        items = sorted_items(state, status=status)
        data = {"ok": True, "items": items}
        if args.json:
            print_json(data)
        else:
            for item in items:
                print(f"{item['status']}: {item['name']}")
        return

    if args.command == "render-telegram":
        result = send_telegram_view(
            state,
            target=args.target,
            account=args.account,
            mode=args.mode,
            thread_id=args.thread_id,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            save_state(path, state)
        print_json(result)
        return

    if args.command == "handle-callback":
        result = handle_callback(
            state,
            callback=args.callback,
            target=args.target,
            account=args.account,
            thread_id=args.thread_id,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            save_state(path, state)
        print_json(result)
        return

    if args.command == "toggle":
        result = toggle_pending(
            state,
            item_id=args.item_id,
            target=args.target,
            account=args.account,
            thread_id=args.thread_id,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            save_state(path, state)
        print_json(result)
        return

    if args.command == "done":
        result = commit_pending(
            state,
            target=args.target,
            account=args.account,
            thread_id=args.thread_id,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            save_state(path, state)
        print_json(result)
        return

    if args.command == "clear-selection":
        result = clear_pending(
            state,
            target=args.target,
            account=args.account,
            thread_id=args.thread_id,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            save_state(path, state)
        print_json(result)
        return

    if changed:
        save_state(path, state)


if __name__ == "__main__":
    main()
