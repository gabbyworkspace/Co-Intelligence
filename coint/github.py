"""GitHub App client (REST, stdlib HTTP + PyJWT for app auth).

Credentials come only from the environment. Installation tokens are cached in
memory and never logged or persisted.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import Settings
from .errors import AuthError, InvalidInput, PermissionDenied, TransientError

API = "https://api.github.com"


class GitHubClient:
    """Interface used by the workflow; see tests/fakes.py for the in-memory fake."""

    def get_commit(self, sha: str) -> dict: ...
    def get_file(self, path: str, ref: str) -> str | None: ...
    def branch_head(self, branch: str) -> str | None: ...
    def default_branch_head(self) -> str: ...
    def commit_files(self, branch: str, files: dict[str, str], message: str) -> str: ...
    def create_comment(self, issue: int, body: str) -> dict: ...
    def close_issue(self, issue: int) -> None: ...
    def create_issue(self, title: str, body: str) -> int: ...
    def create_tag(self, name: str, sha: str) -> None: ...
    def add_labels(self, issue: int, labels: list[str]) -> None: ...
    def list_issue_comments(self, issue: int, since: str | None = None) -> list[dict]: ...
    def list_repo_comments(self, since: str) -> list[dict]: ...
    def file_exists(self, path: str, ref: str) -> bool:
        return self.get_file(path, ref) is not None


class GitHubAppClient(GitHubClient):
    def __init__(self, settings: Settings, timeout: int = 30):
        if not (settings.github_app_id and settings.github_app_private_key and settings.github_installation_id):
            raise AuthError("GitHub App credentials not configured (GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY, "
                            "GITHUB_APP_INSTALLATION_ID)")
        self.s = settings
        self.timeout = timeout
        self._token: str | None = None
        self._token_exp = 0.0
        self.repo_path = f"/repos/{settings.owner}/{settings.repo}"

    # -- auth ---------------------------------------------------------------
    def _app_jwt(self) -> str:
        import jwt  # PyJWT[crypto]
        now = int(time.time())
        return jwt.encode({"iat": now - 60, "exp": now + 540, "iss": self.s.github_app_id},
                          self.s.github_app_private_key, algorithm="RS256")

    def _installation_token(self) -> str:
        if self._token and time.time() < self._token_exp - 300:
            return self._token
        data = self._raw("POST", f"/app/installations/{self.s.github_installation_id}/access_tokens",
                         token=self._app_jwt(), scheme="Bearer")
        self._token = data["token"]
        self._token_exp = time.time() + 3300
        return self._token

    # -- http ---------------------------------------------------------------
    def _raw(self, method: str, path: str, body=None, *, token: str, scheme: str = "token", ok404=False):
        req = urllib.request.Request(API + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None)
        req.add_header("Authorization", f"{scheme} {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "co-intelligence-automation")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            msg = e.read()[:500].decode(errors="replace")
            if e.code == 404 and ok404:
                return None
            if e.code == 401:
                raise AuthError(f"GitHub 401: {msg}")
            if e.code == 403 and "rate limit" not in msg.lower():
                raise PermissionDenied(f"GitHub 403: {msg}")
            if e.code in (403, 429) or e.code >= 500:
                raise TransientError(f"GitHub {e.code}: {msg}")
            if e.code in (404, 409, 422):
                raise InvalidInput(f"GitHub {e.code} {method} {path}: {msg}")
            raise TransientError(f"GitHub {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise TransientError(f"GitHub network error: {e}")

    def _api(self, method: str, path: str, body=None, ok404=False):
        return self._raw(method, path, body, token=self._installation_token(), ok404=ok404)

    # -- repo ---------------------------------------------------------------
    def validate_access(self) -> dict:
        repo = self._api("GET", self.repo_path)
        perms = repo.get("permissions") or {}
        return {"full_name": repo.get("full_name"), "id": repo.get("id"), "permissions": perms}

    def get_commit(self, sha: str) -> dict:
        # Works for unmerged commits on any branch of this repository.
        return self._api("GET", f"{self.repo_path}/commits/{sha}")

    def get_file(self, path: str, ref: str) -> str | None:
        q = urllib.parse.quote(path)
        data = self._api("GET", f"{self.repo_path}/contents/{q}?ref={ref}", ok404=True)
        if data is None:
            return None
        if isinstance(data, list):
            raise InvalidInput(f"{path} is a directory")
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8")
        blob = self._api("GET", f"{self.repo_path}/git/blobs/{data['sha']}")
        return base64.b64decode(blob["content"]).decode("utf-8")

    def branch_head(self, branch: str) -> str | None:
        ref = self._api("GET", f"{self.repo_path}/git/ref/heads/{urllib.parse.quote(branch)}", ok404=True)
        return ref["object"]["sha"] if ref else None

    def default_branch_head(self) -> str:
        repo = self._api("GET", self.repo_path)
        return self.branch_head(repo["default_branch"])

    def commit_files(self, branch: str, files: dict[str, str], message: str) -> str:
        """Commit files on top of the current branch head (creating the branch from
        the default branch if needed). Retries on non-fast-forward races."""
        for _ in range(5):
            head = self.branch_head(branch)
            created = head is None
            if created:
                head = self.default_branch_head()
            base_tree = self._api("GET", f"{self.repo_path}/git/commits/{head}")["tree"]["sha"]
            tree = []
            for path, content in sorted(files.items()):
                blob = self._api("POST", f"{self.repo_path}/git/blobs",
                                 {"content": content, "encoding": "utf-8"})
                tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
            new_tree = self._api("POST", f"{self.repo_path}/git/trees", {"base_tree": base_tree, "tree": tree})
            commit = self._api("POST", f"{self.repo_path}/git/commits",
                               {"message": message, "tree": new_tree["sha"], "parents": [head]})
            try:
                if created:
                    self._api("POST", f"{self.repo_path}/git/refs",
                              {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
                else:
                    self._api("PATCH", f"{self.repo_path}/git/refs/heads/{urllib.parse.quote(branch)}",
                              {"sha": commit["sha"], "force": False})
                return commit["sha"]
            except InvalidInput:
                continue  # head moved (422 not fast-forward / ref exists) - rebuild on new head
        raise TransientError("could not update branch after concurrent updates")

    # -- issues -------------------------------------------------------------
    def create_comment(self, issue: int, body: str) -> dict:
        d = self._api("POST", f"{self.repo_path}/issues/{issue}/comments", {"body": body})
        return {"id": d["id"], "html_url": d["html_url"]}

    def create_tag(self, name: str, sha: str) -> None:
        """Lightweight tag; idempotent when it already points at `sha`, refused otherwise."""
        try:
            self._api("POST", f"{self.repo_path}/git/refs", {"ref": f"refs/tags/{name}", "sha": sha})
        except InvalidInput:
            ref = self._api("GET", f"{self.repo_path}/git/ref/tags/{urllib.parse.quote(name)}", ok404=True)
            if not ref or ref["object"]["sha"] != sha:
                raise PermissionDenied(f"tag {name} already exists at a different commit; tags are never moved")

    def create_issue(self, title: str, body: str) -> int:
        return self._api("POST", f"{self.repo_path}/issues", {"title": title, "body": body})["number"]

    def close_issue(self, issue: int) -> None:
        self._api("PATCH", f"{self.repo_path}/issues/{issue}", {"state": "closed", "state_reason": "completed"})

    def add_labels(self, issue: int, labels: list[str]) -> None:
        self._api("POST", f"{self.repo_path}/issues/{issue}/labels", {"labels": labels})

    def list_issue_comments(self, issue: int, since: str | None = None) -> list[dict]:
        out, page = [], 1
        while True:
            q = f"?per_page=100&page={page}" + (f"&since={since}" if since else "")
            batch = self._api("GET", f"{self.repo_path}/issues/{issue}/comments{q}")
            out.extend(batch)
            if len(batch) < 100:
                return out
            page += 1

    def list_repo_comments(self, since: str) -> list[dict]:
        """All issue comments in the repository updated since `since` (recovery scan)."""
        out, page = [], 1
        while True:
            batch = self._api("GET", f"{self.repo_path}/issues/comments?sort=created&direction=asc"
                                     f"&per_page=100&page={page}&since={since}")
            out.extend(batch)
            if len(batch) < 100 or page >= 10:
                return out
            page += 1
