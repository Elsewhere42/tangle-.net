"""
ServiceNow REST API client for querying change requests.

This module handles all direct communication with the ServiceNow Table API.
It can be tested standalone (python servicenow_client.py) before wiring
it into the AI agent.
"""

import os
import json
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

SERVICENOW_INSTANCE_URL = os.getenv("SERVICENOW_INSTANCE_URL", "").rstrip("/")
SERVICENOW_USERNAME = os.getenv("SERVICENOW_USERNAME", "")
SERVICENOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD", "")

# ServiceNow Table API endpoint for change requests
CHANGE_REQUEST_TABLE = "/api/now/table/change_request"


def _get_auth():
    """Return basic auth tuple for ServiceNow."""
    return (SERVICENOW_USERNAME, SERVICENOW_PASSWORD)


def _get_headers():
    """Standard headers for ServiceNow REST API."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_stale_change_requests(hours_threshold: float = 1.0) -> list[dict]:
    """
    Query ServiceNow for change requests that are still in an open/pending
    state and were created more than `hours_threshold` hours ago.

    ServiceNow "state" field values for change_request:
        -5 = New
        -4 = Assess
        -3 = Authorize
        -2 = Scheduled
        -1 = Implement
         0 = Review
         3 = Closed
         4 = Cancelled

    We look for states that are NOT Closed (3) or Cancelled (4).

    Returns a list of dicts with key fields from each change request.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)
    # ServiceNow datetime format
    cutoff_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")

    # ServiceNow encoded query:
    #   state NOT IN 3,4  (not closed/cancelled)
    #   AND sys_created_on < cutoff  (older than threshold)
    query = (
        f"stateNOT IN3,4"
        f"^sys_created_on<{cutoff_str}"
        f"^ORDERBYDESCsys_created_on"
    )

    params = {
        "sysparm_query": query,
        "sysparm_limit": 50,
        "sysparm_display_value": "true",  # return human-readable values
        "sysparm_fields": ",".join([
            "number",
            "short_description",
            "state",
            "sys_created_on",
            "requested_by",
            "assignment_group",
            "assigned_to",
            "approval",
            "sys_id",
            "priority",
            "category",
        ]),
    }

    url = f"{SERVICENOW_INSTANCE_URL}{CHANGE_REQUEST_TABLE}"

    response = requests.get(
        url,
        auth=_get_auth(),
        headers=_get_headers(),
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    results = response.json().get("result", [])
    return results


def get_change_request_details(change_number: str) -> dict:
    """
    Get full details for a specific change request by its number (e.g. CHG0012345).
    """
    query = f"number={change_number}"

    params = {
        "sysparm_query": query,
        "sysparm_limit": 1,
        "sysparm_display_value": "true",
    }

    url = f"{SERVICENOW_INSTANCE_URL}{CHANGE_REQUEST_TABLE}"

    response = requests.get(
        url,
        auth=_get_auth(),
        headers=_get_headers(),
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    results = response.json().get("result", [])
    if results:
        return results[0]
    return {}


def get_approvers_for_change(sys_id: str) -> list[dict]:
    """
    Get the approvers for a given change request by its sys_id.
    Uses the sysapproval_approver table.
    """
    url = f"{SERVICENOW_INSTANCE_URL}/api/now/table/sysapproval_approver"

    params = {
        "sysparm_query": f"sysapproval={sys_id}",
        "sysparm_display_value": "true",
        "sysparm_fields": "approver,state,sys_updated_on",
    }

    response = requests.get(
        url,
        auth=_get_auth(),
        headers=_get_headers(),
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    return response.json().get("result", [])


# ---------------------------------------------------------------------------
# Standalone test — run this file directly to verify your ServiceNow
# connection before wiring it into the AI agent.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("ServiceNow Connection Test")
    print("=" * 60)
    print(f"Instance: {SERVICENOW_INSTANCE_URL}")
    print(f"Username: {SERVICENOW_USERNAME}")
    print()

    try:
        stale = get_stale_change_requests(hours_threshold=1.0)
        print(f"Found {len(stale)} open change request(s) older than 1 hour:\n")
        for cr in stale:
            print(f"  {cr.get('number', 'N/A'):15s} | "
                  f"State: {cr.get('state', 'N/A'):12s} | "
                  f"Created: {cr.get('sys_created_on', 'N/A'):20s} | "
                  f"{cr.get('short_description', 'N/A')[:50]}")
        print()
        if stale:
            first = stale[0]
            sid = first.get("sys_id", "")
            if sid:
                approvers = get_approvers_for_change(sid)
                print(f"Approvers for {first.get('number', 'N/A')}:")
                for a in approvers:
                    print(f"  - {a.get('approver', 'N/A')} (state: {a.get('state', 'N/A')})")
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to ServiceNow. Check your instance URL.")
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: ServiceNow returned an error: {e}")
    except Exception as e:
        print(f"ERROR: {e}")
