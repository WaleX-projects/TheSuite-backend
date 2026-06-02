import logging
import time
import threading

import requests

logger = logging.getLogger(__name__)

PENDO_TRACK_URL = "https://data.pendo.io/data/track"
PENDO_INTEGRATION_KEY = "7f7b45b4-f93e-4726-8efe-7cddd53010d5"


def track(event, visitor_id="system", account_id="system", properties=None):
    """
    Send a server-side Track Event to Pendo.
    Fires asynchronously so it never blocks the request/response cycle.
    """
    payload = {
        "type": "track",
        "event": event,
        "visitorId": str(visitor_id),
        "accountId": str(account_id),
        "timestamp": int(time.time() * 1000),
    }
    if properties:
        payload["properties"] = properties

    thread = threading.Thread(target=_send, args=(payload,), daemon=True)
    thread.start()


def _send(payload):
    try:
        requests.post(
            PENDO_TRACK_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-pendo-integration-key": PENDO_INTEGRATION_KEY,
            },
            timeout=5,
        )
    except Exception:
        logger.warning("Failed to send Pendo track event: %s", payload.get("event"), exc_info=True)
