import time
from datetime import datetime, timedelta
from integrations.amazon.client import amazon_client
from config import config
from utils.logger import get_logger

logger = get_logger("amazon.reports")

MARKETPLACE = config.AMAZON_MARKETPLACE_ID


def request_report(report_type: str, days_back: int = 7) -> str:
    """Request an SP-API report. Returns reportId."""
    start = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    data = amazon_client.post("/reports/2021-06-30/reports", {
        "reportType": report_type,
        "dataStartTime": start,
        "dataEndTime": end,
        "marketplaceIds": [MARKETPLACE],
    })
    return data.get("reportId", "")


def get_report_status(report_id: str) -> dict:
    return amazon_client.get(f"/reports/2021-06-30/reports/{report_id}")


def wait_for_report(report_id: str, timeout: int = 120) -> str | None:
    """Poll until report is done, return documentId."""
    start = time.time()
    while time.time() - start < timeout:
        status = get_report_status(report_id)
        processing = status.get("processingStatus", "")
        if processing == "DONE":
            return status.get("reportDocumentId")
        if processing in ("CANCELLED", "FATAL"):
            logger.error(f"Report {report_id} failed: {processing}")
            return None
        time.sleep(10)
    return None


def download_report(document_id: str) -> str:
    """Download and return report content as string."""
    import requests
    meta = amazon_client.get(f"/reports/2021-06-30/documents/{document_id}")
    url = meta.get("url", "")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.text


def get_sales_report(days_back: int = 7) -> str:
    report_id = request_report("GET_SALES_AND_TRAFFIC_REPORT", days_back)
    doc_id = wait_for_report(report_id)
    if doc_id:
        return download_report(doc_id)
    return ""


def get_returns_report(days_back: int = 30) -> str:
    report_id = request_report("GET_FBA_FULFILLMENT_CUSTOMER_RETURNS_DATA", days_back)
    doc_id = wait_for_report(report_id)
    if doc_id:
        return download_report(doc_id)
    return ""
