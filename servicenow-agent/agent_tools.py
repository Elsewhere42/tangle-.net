"""
Tool definitions for the Azure AI Foundry agent.

Each tool is a Python function that the agent can call. The agent decides
WHEN to call these based on the user's request and the function descriptions.

The functions here are thin wrappers around servicenow_client.py that return
JSON strings (which is what the agent SDK expects).
"""

import json
from servicenow_client import (
    get_stale_change_requests,
    get_change_request_details,
    get_approvers_for_change,
)


def tool_get_stale_change_requests(hours_threshold: str = "1.0") -> str:
    """
    Find all ServiceNow change requests that are still open and were created
    more than the specified number of hours ago.

    Args:
        hours_threshold: Number of hours. Change requests older than this
                         that are still open will be returned. Default is 1.0.

    Returns:
        JSON string with list of matching change requests including their
        number, state, description, who requested it, and creation time.
    """
    threshold = float(hours_threshold)
    results = get_stale_change_requests(hours_threshold=threshold)
    return json.dumps({
        "count": len(results),
        "change_requests": results,
    }, indent=2)


def tool_get_change_request_details(change_number: str) -> str:
    """
    Get the full details of a specific ServiceNow change request.

    Args:
        change_number: The change request number, e.g. CHG0012345.

    Returns:
        JSON string with all fields of the change request.
    """
    result = get_change_request_details(change_number)
    return json.dumps(result, indent=2)


def tool_get_approvers(sys_id: str) -> str:
    """
    Get the list of approvers for a specific change request.

    Args:
        sys_id: The sys_id of the change request (internal ServiceNow ID).

    Returns:
        JSON string with list of approvers and their approval state.
    """
    results = get_approvers_for_change(sys_id)
    return json.dumps({
        "count": len(results),
        "approvers": results,
    }, indent=2)
