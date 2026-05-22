# DMEPOS Fraud Analysis: AI Assistant

An AI-powered fraud analysis tool for DMEPOS (Durable Medical Equipment, Prosthetics, Orthotics, and Supplies) investigations. The assistant searches official databases - currently only **HHS OIG** and the **Missouri Secretary of State (SOS)** - and returns a plain-language summary and fraud risk analysis for any person, or business you query.

> The rest of the project's dashboards (Open Payments, Suppliers, Referring Providers, Risk Signals) live in Tableau. This repo is the standalone AI Assistant web app only.

---

## What's in this repo

```
index.html → The full-page dark-themed chatbot UI
chat.js → Assistant logic - calls the Render backend, renders responses
```

That's literally it. No build step, no frameworks, no dependencies.

---

## How it works

The frontend is a plain HTML/CSS/JS page hosted on **GitHub Pages**. When a user types a query, `chat.js` sends a `POST` request to the **Render backend**, which hosts a **Gemini** LLM. Based on the question, Gemini selects the appropriate tool from a custom-built **MCP server**. The tool dynamically navigates and scrapes its respective source for information, which Gemini uses to generate a plain-language summary and fraud analysis. The response is rendered back into the chat window.

```
User types query
             ↓
            chat.js
                  ↓
                 POST { message: "..." }
                                      ↓
                                     Render backend
                                                 ↓
                                                Searches HHS OIG / MO SOS
                                                                       ↓ 
                                                                      AI-generated response
                                                                                         ↓
                                                                                       { reply: "..." }
                                                                                                     ↓
                                                                                                    chat.js  
                                                                                                          ↓
                                                                                                         Rendered in chat window
```

### Backend endpoint

```
POST https://randomurl.com
Content-Type: application/json

{ "message": "your query here" }
```

Returns:
```json
{ "reply": "AI-generated summary and fraud analysis..." }
```

Update the `CHAT_ENDPOINT` constant at the top of `chat.js` if the API/URL is different.

---

## Changes to be Done Before Deployment

Nothing major. Change API/URL; The one specified in this js file has been switched off. 

## Deploying to GitHub Pages

Push `index.html` and `chat.js` to your repo. In your GitHub repo settings, go to **Pages** and set the source to the branch and folder containing these files. GitHub Pages will serve `index.html` automatically.

---

## Using the assistant

| Goal | What to type |
|------|-------------|
| Look up a person | Full name - e.g. `John Smith` |
| Look up a business | Business name - e.g. `Acme Medical Supply` |
| Target a specific database | Include `OIG` or `SOS` in your query |

**Limitations to be aware of:**
- Searches one database per question (OIG or SOS). If you don't specify, the AI decides.
- Results are based on the first match returned - not a full list.
- Rate limited to **2 questions per minute**. If you hit an error, wait a moment and try again.
- Data sources: HHS OIG exclusions database and Missouri Secretary of State business registry only.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Plain HTML, CSS, JavaScript |
| Hosting | GitHub Pages |
| Backend / AI | Python on Render |
| Data sources | HHS OIG, Missouri Secretary of State |
| Dashboards | Tableau (separate; not in this repo) |

---

## Backend Repo links
1) MCP repo: https://github.com/N4e-N4e/MCP_Backend_site/tree/main
2) Gemini repo: https://github.com/N4e-N4e/Gemini_Backend_site
