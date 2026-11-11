"""Send a Jenkins result to Webex, or list spaces visible to a bot.

Uses only the Python standard library. No polling loop or inbound Webex
webhook is needed for outbound Jenkins notifications.
"""

import argparse
import getpass
import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

class NoRedirect(HTTPRedirectHandler):
    """Do not forward the Authorization header to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


urlopen = build_opener(NoRedirect()).open
API = "https://webexapis.com/v1/"
STATUSES = ("SUCCESS", "FAILURE", "UNSTABLE", "ABORTED", "NOT_BUILT")


class WebexError(RuntimeError):
    """A safe-to-log error without credentials or response bodies."""


def request_json(url, token, payload=None):
    # The token must never follow an arbitrary pagination URL.
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "webexapis.com" or not parsed.path.startswith("/v1/"):
        raise WebexError("Refusing an unexpected Webex API URL.")
    if not token or token.lower().startswith("bearer "):
        raise WebexError("Supply the bot token only, without the Bearer prefix.")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urlopen(request, timeout=30) as response:
            if not 200 <= response.status < 300:
                raise WebexError(f"Webex returned HTTP {response.status}.")
            return json.loads(response.read().decode("utf-8")), response.headers
    except HTTPError as exc:
        hints = {
            400: "Check the room ID and request fields.",
            401: "Check or regenerate the bot access token.",
            403: "Check that the bot is allowed to post in this space.",
            404: "Check the room ID and add the bot to that space.",
            429: "Rate limit reached; wait before retrying.",
        }
        raise WebexError(f"Webex HTTP {exc.code}. {hints.get(exc.code, 'Check Webex service availability.')} ") from None
    except (URLError, TimeoutError, OSError):
        raise WebexError("Cannot reach Webex; check network, DNS, proxy and TLS settings.") from None
    except (ValueError, UnicodeError):
        raise WebexError("Webex returned an invalid JSON response.") from None


def build_message(status, env):
    if status not in STATUSES:
        raise ValueError("Unsupported Jenkins build status")
    completed = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return "\n".join([
        f"Jenkins build/tests: {status}",
        f"Job: {env.get('JOB_NAME', 'manual-check')}",
        f"Build: #{env.get('BUILD_NUMBER', 'local')}",
        f"Branch: {env.get('GIT_BRANCH', 'unknown')}",
        f"Commit: {env.get('GIT_COMMIT', 'unknown')}",
        f"Results: {env.get('BUILD_URL', 'not available')}",
        f"Reported: {completed}",
    ])


def send_notification(status, env):
    token = env.get("WEBEX_BOT_TOKEN", "").strip()
    room = env.get("WEBEX_ROOM_ID", "").strip()
    if not token or not room:
        raise WebexError("WEBEX_BOT_TOKEN and WEBEX_ROOM_ID must be set through Jenkins credentials.")
    response, _ = request_json(API + "messages", token, {"roomId": room, "text": build_message(status, env)})
    if not isinstance(response, dict) or not response.get("id"):
        raise WebexError("Webex did not confirm a created message ID.")
    print("Webex notification sent successfully.")


def list_rooms(token):
    url = API + "rooms?max=100"
    seen = set()
    count = 0
    while url:
        if url in seen:
            raise WebexError("Webex returned a repeated pagination URL.")
        seen.add(url)
        response, headers = request_json(url, token)
        if not isinstance(response, dict) or not isinstance(response.get("items"), list):
            raise WebexError("Webex returned an unexpected room list.")
        for room in response["items"]:
            print(f"Space: {room.get('title', '(untitled)')}\nType: {room.get('type', 'unknown')}\nRoom ID: {room['id']}\n")
            count += 1
        next_link = re.search(r'<([^>]+)>\s*;\s*rel="next"', headers.get("Link", ""))
        url = next_link.group(1) if next_link else None
    if count == 0:
        print("No spaces found. Add the bot's email address to your Webex space, then run again.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list-rooms", help="Enter the bot token at a hidden prompt; list its spaces")
    notify = commands.add_parser("notify", help="Send one result using Jenkins environment variables")
    notify.add_argument("--status", required=True, choices=STATUSES)
    args = parser.parse_args()
    try:
        if args.command == "list-rooms":
            token = os.environ.get("WEBEX_BOT_TOKEN", "").strip() or getpass.getpass("Webex bot token (hidden; no Bearer prefix): ").strip()
            list_rooms(token)
        else:
            send_notification(args.status, os.environ)
    except (WebexError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
