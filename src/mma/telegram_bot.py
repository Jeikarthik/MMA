"""Minimal Telegram Bot API adapter."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from typing import Any
from urllib import error, parse, request

from mma.services import MmaService


class TelegramError(RuntimeError):
    """Raised when Telegram integration fails."""


class TelegramBot:
    def __init__(self, token: str, service: MmaService) -> None:
        self.token = token
        self.service = service
        self.base_url = f"https://api.telegram.org/bot{token}"

    def poll_forever(self, *, interval_seconds: int = 2) -> None:
        offset = 0
        while True:
            updates = self.get_updates(offset=offset)
            for update in updates:
                offset = max(offset, int(update["update_id"]) + 1)
                message = update.get("message") or {}
                chat = message.get("chat") or {}
                text = message.get("text") or ""
                chat_id = chat.get("id")
                if chat_id is None or not text:
                    continue
                if self.service.config.telegram_allowed_chat_ids and int(chat_id) not in self.service.config.telegram_allowed_chat_ids:
                    self.send_message(chat_id, "MMA access denied for this chat.")
                    continue
                self.send_message(chat_id, handle_command(self.service, text))
            time.sleep(interval_seconds)

    def get_updates(self, *, offset: int) -> list[dict[str, Any]]:
        query = parse.urlencode({"timeout": 20, "offset": offset})
        data = self._request_json("GET", f"/getUpdates?{query}")
        if not data.get("ok"):
            raise TelegramError("Telegram getUpdates failed")
        return data.get("result", [])

    def send_message(self, chat_id: int, text: str) -> None:
        payload = {"chat_id": chat_id, "text": text}
        data = self._request_json("POST", "/sendMessage", payload)
        if not data.get("ok"):
            raise TelegramError("Telegram sendMessage failed")

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = request.Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, error.URLError, json.JSONDecodeError) as exc:
            raise TelegramError(str(exc)) from exc


def handle_command(service: MmaService, text: str) -> str:
    """Handle the initial Telegram command set."""

    command, _, rest = text.strip().partition(" ")
    if command == "/start":
        return "MMA ready. Use /new_task, /status, /run, /capabilities, or /resources."
    if command == "/new_task":
        if not rest.strip():
            return "Usage: /new_task describe the engineering task"
        task = service.create_task(description=rest.strip())
        return f"Created task {task['id'][:8]}: {task['status']}"
    if command == "/status":
        tasks = service.list_tasks()
        if not tasks:
            return "No tasks yet."
        return "\n".join(f"{task['id'][:8]} {task['status']} {task['title']}" for task in tasks)
    if command == "/run":
        if not rest.strip():
            return "Usage: /run TASK_ID"
        result = service.run_task(rest.strip())
        return f"{result['status']}: {result['message']}"
    if command == "/retry":
        if not rest.strip():
            return "Usage: /retry TASK_ID"
        return service.retry_task(rest.strip())["status"]
    if command == "/rollback":
        if not rest.strip():
            return "Usage: /rollback TASK_ID"
        return service.rollback_task(rest.strip())["status"]
    if command == "/pause":
        if not rest.strip():
            return "Usage: /pause TASK_ID"
        return service.pause_task(rest.strip())["status"]
    if command == "/answer_asset":
        request_id, sep, answer = rest.partition(" ")
        if not sep:
            return "Usage: /answer_asset REQUEST_ID answer text"
        result = service.answer_asset(request_id, answer)
        return result["status"]
    if command == "/provider_health":
        return json.dumps(service.provider_health(), indent=2)
    if command == "/capabilities":
        capabilities = service.capabilities()
        return "\n".join(
            f"{capability['name']} ({'approval' if capability['requires_approval'] else 'read-only'})"
            for capability in capabilities
        )
    if command == "/resources":
        status = service.resource_status()
        return json.dumps(status, indent=2)
    return "Unknown command. Use /start for help."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mma-telegram")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--token", default=os.getenv("TELEGRAM_BOT_TOKEN"))
    args = parser.parse_args(argv)
    if not args.token:
        raise TelegramError("TELEGRAM_BOT_TOKEN is not configured")
    TelegramBot(args.token, MmaService(Path(args.repo))).poll_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
