import hashlib
import hmac
import time
import requests
from config import config
from utils.logger import get_logger

logger = get_logger("myntra.client")


class MyntraClient:
    """Myntra Seller API client with HMAC authentication."""

    BASE_URL = config.MYNTRA_BASE_URL

    def _sign_request(self, method: str, path: str, timestamp: str) -> str:
        message = f"{method}\n{path}\n{timestamp}"
        signature = hmac.new(
            config.MYNTRA_API_SECRET.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _headers(self, method: str, path: str) -> dict:
        timestamp = str(int(time.time()))
        signature = self._sign_request(method, path, timestamp)
        return {
            "X-Myntra-ApiKey": config.MYNTRA_API_KEY,
            "X-Myntra-Timestamp": timestamp,
            "X-Myntra-Signature": signature,
            "Content-Type": "application/json",
        }

    def get(self, path: str, params: dict = None) -> dict:
        url = f"{self.BASE_URL}{path}"
        headers = self._headers("GET", path)
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt == 2:
                    logger.error(f"Myntra GET {path} failed: {e}")
                    raise
                time.sleep(2 ** attempt)

    def post(self, path: str, body: dict) -> dict:
        url = f"{self.BASE_URL}{path}"
        headers = self._headers("POST", path)
        for attempt in range(3):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt == 2:
                    logger.error(f"Myntra POST {path} failed: {e}")
                    raise
                time.sleep(2 ** attempt)

    def put(self, path: str, body: dict) -> dict:
        url = f"{self.BASE_URL}{path}"
        headers = self._headers("PUT", path)
        resp = requests.put(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()


myntra_client = MyntraClient()
