"""Gmail API client for the JARVIS mailbox (OAuth2 refresh token from env).

Send outcome classification:
  - DefinitePreSendFailure: the request never reached Gmail or Gmail explicitly
    refused it (connect error, 4xx incl. 429). Safe to retry.
  - UncertainSendOutcome: request may have been accepted (timeout/reset after
    sending, 5xx). Must reconcile before any resend.
"""
from __future__ import annotations

import base64
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from .config import Settings
from .errors import AuthError, CointError, PermissionDenied


class DefinitePreSendFailure(CointError):
    pass


class UncertainSendOutcome(CointError):
    pass


class GmailClient:
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self, settings: Settings, timeout: int = 30):
        if not (settings.gmail_client_id and settings.gmail_client_secret and settings.gmail_refresh_token):
            raise AuthError("Gmail OAuth not configured (GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN)")
        self.s = settings
        self.timeout = timeout

    def _token(self) -> str:
        body = urllib.parse.urlencode({
            "client_id": self.s.gmail_client_id, "client_secret": self.s.gmail_client_secret,
            "refresh_token": self.s.gmail_refresh_token, "grant_type": "refresh_token"}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(self.TOKEN_URL, data=body), timeout=self.timeout) as r:
                return json.loads(r.read())["access_token"]
        except urllib.error.HTTPError as e:
            if e.code in (400, 401):
                raise AuthError(f"Gmail token refresh failed: {e.read()[:300]!r}")
            raise DefinitePreSendFailure(f"token endpoint {e.code}")
        except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
            raise DefinitePreSendFailure(f"token endpoint unreachable: {e}")

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(self.API + path)
        req.add_header("Authorization", f"Bearer {self._token()}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise AuthError("Gmail 401")
            if e.code == 403:
                raise PermissionDenied("Gmail 403")
            raise DefinitePreSendFailure(f"Gmail GET {e.code}")
        except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
            raise DefinitePreSendFailure(f"Gmail unreachable: {e}")

    def authorized_address(self) -> str:
        return self._get("/profile")["emailAddress"].lower()

    def find_sent_by_message_id(self, rfc822_message_id: str) -> dict | None:
        q = urllib.parse.quote(f"in:anywhere rfc822msgid:{rfc822_message_id.strip('<>')}")
        res = self._get(f"/messages?q={q}&maxResults=5")
        msgs = res.get("messages") or []
        return msgs[0] if msgs else None

    def send_raw(self, raw_rfc822: bytes) -> dict:
        token = self._token()  # failures here are definitely pre-send
        req = urllib.request.Request(self.API + "/messages/send", method="POST",
                                     data=json.dumps({"raw": base64.urlsafe_b64encode(raw_rfc822).decode()}).encode())
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise AuthError("Gmail 401 on send")
            if e.code == 403:
                raise PermissionDenied("Gmail 403 on send")
            if e.code < 500:
                raise DefinitePreSendFailure(f"Gmail refused send: {e.code}")
            raise UncertainSendOutcome(f"Gmail {e.code} on send")
        except urllib.error.URLError as e:
            if isinstance(e.reason, (ConnectionRefusedError, socket.gaierror)):
                raise DefinitePreSendFailure(f"Gmail unreachable: {e}")
            raise UncertainSendOutcome(f"network error during send: {e}")
        except (socket.timeout, TimeoutError, ConnectionError) as e:
            raise UncertainSendOutcome(f"timeout/reset during send: {e}")
