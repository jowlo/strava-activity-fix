"""Strava API client with OAuth2 token management."""

import json
import os
import time
from pathlib import Path

import requests


STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


class StravaClient:
    def __init__(self, client_id: str, client_secret: str, tokens_path: str = "tokens.json"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tokens_path = tokens_path
        self.access_token = None
        self.refresh_token = None
        self.expires_at = 0
        self._load_tokens()

    def _load_tokens(self):
        """Load stored tokens from disk."""
        if Path(self.tokens_path).exists():
            with open(self.tokens_path, "r") as f:
                data = json.load(f)
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.expires_at = data.get("expires_at", 0)

    def _save_tokens(self):
        """Persist tokens to disk."""
        Path(self.tokens_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.tokens_path, "w") as f:
            json.dump({
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.expires_at,
            }, f, indent=2)

    def is_authenticated(self) -> bool:
        """Check if we have tokens (may be expired but refreshable)."""
        return self.refresh_token is not None

    def get_auth_url(self, redirect_uri: str = "http://localhost:8000/callback") -> str:
        """Generate the OAuth2 authorization URL."""
        return (
            f"{STRAVA_AUTH_URL}?client_id={self.client_id}"
            f"&response_type=code&redirect_uri={redirect_uri}"
            f"&scope=activity:read_all,activity:write"
        )

    def exchange_code(self, code: str):
        """Exchange authorization code for tokens."""
        resp = requests.post(STRAVA_TOKEN_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
        })
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.expires_at = data["expires_at"]
        self._save_tokens()

    def _ensure_token(self):
        """Refresh the access token if expired."""
        if time.time() >= self.expires_at - 60:
            if not self.refresh_token:
                raise RuntimeError("No refresh token available. Re-authenticate.")
            resp = requests.post(STRAVA_TOKEN_URL, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            })
            resp.raise_for_status()
            data = resp.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            self.expires_at = data["expires_at"]
            self._save_tokens()

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an authenticated API request."""
        self._ensure_token()
        url = f"{STRAVA_API_BASE}{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        resp = requests.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp

    def get_activities(self, after: int = None, per_page: int = 30) -> list:
        """Fetch recent activities."""
        params = {"per_page": per_page}
        if after:
            params["after"] = after
        return self._request("GET", "/athlete/activities", params=params).json()

    def get_activity(self, activity_id: int) -> dict:
        """Fetch a single activity with full details."""
        return self._request("GET", f"/activities/{activity_id}").json()

    def update_activity(self, activity_id: int, updates: dict) -> dict:
        """Update an activity's mutable fields."""
        return self._request("PUT", f"/activities/{activity_id}", json=updates).json()

    def delete_activity(self, activity_id: int):
        """Delete an activity."""
        self._request("DELETE", f"/activities/{activity_id}")

    def hide_activity(self, activity_id: int):
        """Hide an activity by setting visibility to 'only_me'."""
        return self.update_activity(activity_id, {"hide_from_home": True})

    def mute_activity(self, activity_id: int):
        """Mute an activity (no feed post)."""
        return self.update_activity(activity_id, {"hide_from_home": True})
