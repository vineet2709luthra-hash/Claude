from integrations.myntra.client import myntra_client
from utils.logger import get_logger

logger = get_logger("myntra.returns")


def get_return_requests() -> list[dict]:
    data = myntra_client.get("/v1/returns", params={"status": "requested", "limit": 100})
    return data.get("returns", [])


def approve_return(return_id: str) -> dict:
    return myntra_client.post(f"/v1/returns/{return_id}/approve", {})


def reject_return(return_id: str, reason: str) -> dict:
    return myntra_client.post(f"/v1/returns/{return_id}/reject", {"reason": reason})


def get_return_details(return_id: str) -> dict:
    return myntra_client.get(f"/v1/returns/{return_id}")
