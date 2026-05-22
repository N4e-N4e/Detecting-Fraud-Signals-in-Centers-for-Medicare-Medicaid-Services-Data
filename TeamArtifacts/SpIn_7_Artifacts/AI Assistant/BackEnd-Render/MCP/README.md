# DEMIrobato (DMEPOS Fraud Analysis AI Assistant) — MCP

Web scraping tools exposed as MCP (Model Context Protocol) tools. Used by the Gemini backend to search real government databases.

## What it does

- **OIG Search** — scrapes the HHS OIG website for fraud cases, exclusions, audits, and enforcement actions
- **SOS Search** — scrapes the Missouri Secretary of State database for business entity registration info

## Tools

| Tool | Description |
|---|---|
| `OIG_search(item)` | Searches HHS OIG for a name, company, or keyword |
| `SOS_search(item)` | Searches MO SOS business entity database |

Both tools use headless Chrome (Selenium) to navigate and extract page content, then return structured data back to the API.

## Setup

Install dependencies:
```bash
pip install -r requirements.txt
```

Requirements: `fastapi`, `uvicorn`, `selenium`, `webdriver-manager`, `mcp`, `pydantic`

**Chrome is required.** On Render, the build script (`render_build.sh`) handles downloading Chrome automatically.

### Environment Variables

| Variable | Description |
|---|---|
| `nResult` | Number of results to return per search (default: `1`) |


## Deploying on Render

The `render_build.sh` script will:
1. Install Python dependencies
2. Download and cache Chrome to `/opt/render/project/.render/chrome`

Set the build command to `./render_build.sh` in your Render service settings.

---

> Part of the DMEPOS Healthcare Fraud Analysis tool suite.
