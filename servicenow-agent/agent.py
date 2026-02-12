"""
Azure AI Foundry Agent — ServiceNow Stale Change Request Monitor

This is the main entry point. It creates an AI agent in Azure AI Foundry
that can query ServiceNow for stale change requests using function-calling
tools.

How it works:
  1. Connects to your Azure AI Foundry project
  2. Creates an agent with a GPT-4o model and custom tools
  3. Sends the agent a prompt asking it to find stale change requests
  4. The agent autonomously calls the ServiceNow tools to gather data
  5. The agent produces a human-readable summary

Usage:
  python agent.py
"""

import os

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionTool, ToolSet

from dotenv import load_dotenv

from agent_tools import (
    tool_get_stale_change_requests,
    tool_get_change_request_details,
    tool_get_approvers,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_CONNECTION_STRING = os.getenv("AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING", "")
MODEL_DEPLOYMENT = "gpt-4o"  # name of your model deployment in Foundry

# The system prompt tells the agent WHO it is and HOW to behave
SYSTEM_PROMPT = """You are a ServiceNow Change Request Monitor agent.

Your job is to:
1. Find change requests in ServiceNow that are still open and older than 1 hour.
2. For each stale change request, retrieve the approver information.
3. Produce a clear summary report listing:
   - Change request number
   - Short description
   - Current state
   - How long it has been open
   - Who submitted it (requested_by)
   - Who the approver(s) are and their approval state
   - Priority level

Format the report as a clear, readable table or list.
If no stale change requests are found, say so clearly.

Always call get_stale_change_requests first, then for each result
that has a sys_id, call get_approvers to find the approver details.
"""

# ---------------------------------------------------------------------------
# Define the tools the agent can call
# ---------------------------------------------------------------------------
# The agent SDK uses these definitions to know what functions are available,
# what parameters they accept, and when to call them.

user_functions = {
    "tool_get_stale_change_requests": tool_get_stale_change_requests,
    "tool_get_change_request_details": tool_get_change_request_details,
    "tool_get_approvers": tool_get_approvers,
}


def run_agent():
    """Create and run the ServiceNow monitoring agent."""

    # Connect to Azure AI Foundry
    client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=PROJECT_CONNECTION_STRING,
    )

    # Create a FunctionTool from our Python functions.
    # The SDK inspects the function signatures and docstrings to build
    # the tool schemas automatically.
    function_tool = FunctionTool(functions=list(user_functions.values()))

    toolset = ToolSet()
    toolset.add(function_tool)

    # Create the agent
    agent = client.agents.create_agent(
        model=MODEL_DEPLOYMENT,
        name="ServiceNow Change Monitor",
        instructions=SYSTEM_PROMPT,
        toolset=toolset,
    )
    print(f"Created agent: {agent.id}")

    # Create a conversation thread
    thread = client.agents.threads.create()
    print(f"Created thread: {thread.id}")

    # Send the user message that kicks off the agent's work
    message = client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "Please find all open change requests that have been open for "
            "more than 1 hour. For each one, look up the approvers. "
            "Give me a summary report."
        ),
    )

    # Run the agent — it will call tools as needed and produce a response.
    # process_and_poll handles the tool-calling loop automatically:
    #   Agent decides to call a tool -> SDK executes the function ->
    #   result sent back to agent -> agent decides next step or responds.
    run = client.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent.id,
    )

    print(f"\nRun status: {run.status}")

    if run.status == "failed":
        print(f"Error: {run.last_error}")
        return

    # Retrieve and print the agent's response
    messages = client.agents.messages.list(thread_id=thread.id)

    # Messages are returned newest-first; the last assistant message is the response
    for msg in messages:
        if msg.role == "assistant":
            for content_block in msg.content:
                if hasattr(content_block, "text"):
                    print("\n" + "=" * 60)
                    print("AGENT REPORT")
                    print("=" * 60)
                    print(content_block.text.value)
            break

    # Clean up — delete the agent (the thread persists for history)
    client.agents.delete_agent(agent.id)
    print(f"\nCleaned up agent: {agent.id}")


if __name__ == "__main__":
    run_agent()
