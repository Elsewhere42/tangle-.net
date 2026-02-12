# ServiceNow Change Request Monitor — Azure AI Foundry Agent

## Overview

This agent connects to ServiceNow via its REST API, finds change requests
that have been open for more than 1 hour, retrieves approver information,
and produces a summary report.

## Architecture

```
You (or scheduler)
  │
  ▼
agent.py  ──►  Azure AI Foundry (GPT-4o)
                  │
                  │ function calling
                  ▼
              agent_tools.py  ──►  servicenow_client.py  ──►  ServiceNow API
```

**How the pieces fit together:**

| File | Purpose |
|---|---|
| `servicenow_client.py` | Low-level ServiceNow REST API calls (can be tested standalone) |
| `agent_tools.py` | Wraps the client functions into tool format the AI agent can call |
| `agent.py` | Creates the Azure AI Foundry agent, sends a prompt, processes the response |
| `.env` | Your credentials (never committed to git) |

## Prerequisites — What to Request

### 1. Azure AI Foundry Project (REQUIRED)
Request from your Azure/Cloud team:
- An **Azure AI Foundry Hub** and **Project**
- A **GPT-4o model deployment** within the project
- Your user account added with **Contributor** role on the project
- You will need the **Project Connection String** from the Foundry portal
  (found under Project Settings > Overview)

### 2. ServiceNow API Access (ALREADY HAVE)
You need:
- Instance URL (e.g., `https://yourcompany.service-now.com`)
- Service account username and password
- The account needs READ access to:
  - `change_request` table
  - `sysapproval_approver` table

### 3. Local Development Environment
- Python 3.10 or higher
- `pip` for installing packages
- Access to install Python packages (or a virtual environment)

## Setup Steps

### Step 1: Clone and set up

```bash
cd servicenow-agent
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### Step 2: Configure credentials

```bash
cp .env.example .env
# Edit .env with your actual values
```

### Step 3: Test the ServiceNow connection (no AI involved yet)

```bash
python servicenow_client.py
```

This will connect directly to ServiceNow and print any stale change requests.
**Do this first** to confirm your credentials and network access work.

### Step 4: Authenticate with Azure

```bash
az login
```

The agent uses `DefaultAzureCredential`, which picks up your Azure CLI login.

### Step 5: Run the full agent

```bash
python agent.py
```

## What the Agent Does (Step by Step)

1. Connects to your Azure AI Foundry project
2. Creates a temporary AI agent with GPT-4o and your custom tools
3. Sends the agent this prompt: "Find all open change requests older than 1 hour"
4. The agent **autonomously decides** to call `tool_get_stale_change_requests()`
5. Your Python function executes, hits the ServiceNow API, returns JSON
6. The agent reads the JSON results
7. For each change request, the agent calls `tool_get_approvers()` with the sys_id
8. Once it has all the data, the agent writes a human-readable summary report
9. The script prints the report and cleans up the agent

## Phase 2: Email Notifications (Future)

Once you determine your email system (Microsoft 365, SendGrid, etc.),
we will add a `send_notification()` tool that the agent can call to
email the submitter and approver for each stale change request.

## Troubleshooting

| Problem | Solution |
|---|---|
| `ConnectionError` on ServiceNow | Check VPN, check instance URL in .env |
| `401 Unauthorized` from ServiceNow | Check username/password in .env |
| `403 Forbidden` from ServiceNow | Service account may lack table read permissions |
| `DefaultAzureCredential` errors | Run `az login` first |
| Agent run status = `failed` | Check model deployment name matches `MODEL_DEPLOYMENT` in agent.py |
