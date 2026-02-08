"""GitHub work evidence collector using gh CLI with REST API fallback."""

import json
import logging
import subprocess
import os
import requests as http_requests

from models import new_evidence

logger = logging.getLogger("smartokr")


class GitHubCollector:
    def __init__(self, token: str = ""):
        self.token = token
        self._has_gh = self._check_gh_cli()

    def _check_gh_cli(self) -> bool:
        try:
            subprocess.run(["gh", "--version"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def collect(self, owner: str, repo: str, author: str, since: str, until: str,
                evidence_types: list = None) -> dict:
        """Collect work evidence from GitHub.

        Returns dict with commits, pull_requests, issues arrays and summary.
        """
        types = evidence_types or ["commits", "pull_requests", "issues"]
        result = {"commits": [], "pull_requests": [], "issues": [], "evidence_items": []}

        if "commits" in types:
            commits = self._collect_commits(owner, repo, author, since, until)
            result["commits"] = commits
            for c in commits:
                ev = new_evidence(
                    person=author,
                    title=c.get("message", "")[:200],
                    description=c.get("message", ""),
                    source_type="github_commit",
                    date_str=c.get("date", ""),
                    url=c.get("url", ""),
                    metadata={
                        "repo": f"{owner}/{repo}",
                        "sha": c.get("sha", ""),
                    },
                    tags=["github", "commit"],
                )
                result["evidence_items"].append(ev)

        if "pull_requests" in types:
            prs = self._collect_prs(owner, repo, author, since, until)
            result["pull_requests"] = prs
            for pr in prs:
                ev = new_evidence(
                    person=author,
                    title=pr.get("title", ""),
                    description=f"PR #{pr.get('number', '')}: {pr.get('title', '')}",
                    source_type="github_pr",
                    date_str=pr.get("created_at", ""),
                    url=pr.get("url", ""),
                    metadata={
                        "repo": f"{owner}/{repo}",
                        "pr_number": pr.get("number"),
                        "state": pr.get("state", ""),
                    },
                    tags=["github", "pull_request"],
                )
                result["evidence_items"].append(ev)

        if "issues" in types:
            issues = self._collect_issues(owner, repo, author, since, until)
            result["issues"] = issues
            for iss in issues:
                ev = new_evidence(
                    person=author,
                    title=iss.get("title", ""),
                    description=f"Issue #{iss.get('number', '')}: {iss.get('title', '')}",
                    source_type="github_issue",
                    date_str=iss.get("created_at", ""),
                    url=iss.get("url", ""),
                    metadata={
                        "repo": f"{owner}/{repo}",
                        "issue_number": iss.get("number"),
                        "state": iss.get("state", ""),
                    },
                    tags=["github", "issue"],
                )
                result["evidence_items"].append(ev)

        result["summary"] = {
            "commits_count": len(result["commits"]),
            "prs_count": len(result["pull_requests"]),
            "issues_count": len(result["issues"]),
            "total_evidence": len(result["evidence_items"]),
        }
        return result

    # --- Commits ---

    def _collect_commits(self, owner, repo, author, since, until) -> list:
        if self._has_gh:
            return self._gh_commits(owner, repo, author, since, until)
        return self._api_commits(owner, repo, author, since, until)

    def _gh_commits(self, owner, repo, author, since, until) -> list:
        try:
            cmd = [
                "gh", "api", f"/repos/{owner}/{repo}/commits",
                "--paginate",
                "-f", f"author={author}",
                "-f", f"since={since}T00:00:00Z",
                "-f", f"until={until}T23:59:59Z",
                "-f", "per_page=100",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.warning(f"gh commits failed: {result.stderr}")
                return self._api_commits(owner, repo, author, since, until)

            items = json.loads(result.stdout) if result.stdout.strip() else []
            if not isinstance(items, list):
                items = []
            return [
                {
                    "sha": c.get("sha", "")[:7],
                    "message": c.get("commit", {}).get("message", "").split("\n")[0],
                    "date": c.get("commit", {}).get("author", {}).get("date", ""),
                    "url": c.get("html_url", ""),
                }
                for c in items
            ]
        except Exception as e:
            logger.warning(f"gh commits exception: {e}")
            return self._api_commits(owner, repo, author, since, until)

    def _api_commits(self, owner, repo, author, since, until) -> list:
        if not self.token:
            return []
        headers = {"Authorization": f"token {self.token}", "Accept": "application/vnd.github+json"}
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {
            "author": author,
            "since": f"{since}T00:00:00Z",
            "until": f"{until}T23:59:59Z",
            "per_page": 100,
        }
        try:
            resp = http_requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            items = resp.json()
            return [
                {
                    "sha": c.get("sha", "")[:7],
                    "message": c.get("commit", {}).get("message", "").split("\n")[0],
                    "date": c.get("commit", {}).get("author", {}).get("date", ""),
                    "url": c.get("html_url", ""),
                }
                for c in items
            ]
        except Exception as e:
            logger.warning(f"API commits failed: {e}")
            return []

    # --- Pull Requests ---

    def _collect_prs(self, owner, repo, author, since, until) -> list:
        if self._has_gh:
            return self._gh_prs(owner, repo, author, since, until)
        return self._api_prs(owner, repo, author, since, until)

    def _gh_prs(self, owner, repo, author, since, until) -> list:
        try:
            query = f"repo:{owner}/{repo} author:{author} created:{since}..{until} is:pr"
            cmd = [
                "gh", "api", "/search/issues",
                "-f", f"q={query}",
                "-f", "per_page=100",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return self._api_prs(owner, repo, author, since, until)

            data = json.loads(result.stdout) if result.stdout.strip() else {}
            items = data.get("items", [])
            return [
                {
                    "number": pr.get("number"),
                    "title": pr.get("title", ""),
                    "state": pr.get("state", ""),
                    "created_at": pr.get("created_at", ""),
                    "url": pr.get("html_url", ""),
                }
                for pr in items
            ]
        except Exception as e:
            logger.warning(f"gh PRs exception: {e}")
            return self._api_prs(owner, repo, author, since, until)

    def _api_prs(self, owner, repo, author, since, until) -> list:
        if not self.token:
            return []
        headers = {"Authorization": f"token {self.token}", "Accept": "application/vnd.github+json"}
        query = f"repo:{owner}/{repo} author:{author} created:{since}..{until} is:pr"
        url = "https://api.github.com/search/issues"
        try:
            resp = http_requests.get(url, headers=headers, params={"q": query, "per_page": 100}, timeout=15)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [
                {
                    "number": pr.get("number"),
                    "title": pr.get("title", ""),
                    "state": pr.get("state", ""),
                    "created_at": pr.get("created_at", ""),
                    "url": pr.get("html_url", ""),
                }
                for pr in items
            ]
        except Exception as e:
            logger.warning(f"API PRs failed: {e}")
            return []

    # --- Issues ---

    def _collect_issues(self, owner, repo, author, since, until) -> list:
        if self._has_gh:
            return self._gh_issues(owner, repo, author, since, until)
        return self._api_issues(owner, repo, author, since, until)

    def _gh_issues(self, owner, repo, author, since, until) -> list:
        try:
            query = f"repo:{owner}/{repo} author:{author} created:{since}..{until} is:issue"
            cmd = [
                "gh", "api", "/search/issues",
                "-f", f"q={query}",
                "-f", "per_page=100",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return self._api_issues(owner, repo, author, since, until)

            data = json.loads(result.stdout) if result.stdout.strip() else {}
            items = data.get("items", [])
            return [
                {
                    "number": iss.get("number"),
                    "title": iss.get("title", ""),
                    "state": iss.get("state", ""),
                    "created_at": iss.get("created_at", ""),
                    "url": iss.get("html_url", ""),
                }
                for iss in items
            ]
        except Exception as e:
            logger.warning(f"gh issues exception: {e}")
            return self._api_issues(owner, repo, author, since, until)

    def _api_issues(self, owner, repo, author, since, until) -> list:
        if not self.token:
            return []
        headers = {"Authorization": f"token {self.token}", "Accept": "application/vnd.github+json"}
        query = f"repo:{owner}/{repo} author:{author} created:{since}..{until} is:issue"
        url = "https://api.github.com/search/issues"
        try:
            resp = http_requests.get(url, headers=headers, params={"q": query, "per_page": 100}, timeout=15)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [
                {
                    "number": iss.get("number"),
                    "title": iss.get("title", ""),
                    "state": iss.get("state", ""),
                    "created_at": iss.get("created_at", ""),
                    "url": iss.get("html_url", ""),
                }
                for iss in items
            ]
        except Exception as e:
            logger.warning(f"API issues failed: {e}")
            return []
