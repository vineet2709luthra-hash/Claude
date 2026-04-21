import requests
import time
from datetime import datetime, timedelta
from config import config
from utils.logger import get_logger

logger = get_logger("amazon.client")

TOKEN_URL = "https://api.amazon.com/auth/o2/token"
SP_API_BASE = "https://sellingpartnerapi-fe.amazon.com"  # change to -na for US, -eu for EU


class AmazonClient:
    """Low-level Amazon SP-API HTTP client with auto token refresh."""

    def __init__(self):
        self._access_token: str | None = None
        self._token_expiry: datetime = datetime.utcnow()

    def _refresh_token(self):
        resp = requests.post(TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": config.AMAZON_REFRESH_TOKEN,
            "client_id": config.AMAZON_CLIENT_ID,
            "client_secret": config.AMAZON_CLIENT_SECRET,
        })
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expiry = datetime.utcnow() + timedelta(seconds=data["expires_in"] - 60)
        logger.info("Amazon access token refreshed.")

    def _get_token(self) -> str:
        if not self._access_token or datetime.utcnow() >= self._token_expiry:
            self._refresh_token()
        return self._access_token

    def _headers(self) -> dict:
        return {
            "x-amz-access-token": self._get_token(),
            "Content-Type": "application/json",
        }

    def get(self, path: str, params: dict = None) -> dict:
        url = f"{SP_API_BASE}{path}"
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited. Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt == 2:
                    logger.error(f"Amazon GET {path} failed: {e}")
                    raise
                time.sleep(2 ** attempt)

    def post(self, path: str, body: dict) -> dict:
        url = f"{SP_API_BASE}{path}"
        for attempt in range(3):
            try:
                resp = requests.post(url, headers=self._headers(), json=body, timeout=30)
                if resp.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt == 2:
                    logger.error(f"Amazon POST {path} failed: {e}")
                    raise
                time.sleep(2 ** attempt)

    def patch(self, path: str, body: dict) -> dict:
        url = f"{SP_API_BASE}{path}"
        resp = requests.patch(url, headers=self._headers(), json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()


amazon_client = AmazonClient()
