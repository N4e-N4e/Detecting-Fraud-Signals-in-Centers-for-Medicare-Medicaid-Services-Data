# Detecting Fraud Signals in Centers for Medicare & Medicaid Services Data

> **DSA Capstone Project - University of Missouri**

## Team
| Name | Track |
|---|---|
| Sabrina Woo | BioHealth Analytics |
| Love Ayinde | High-Performance Computing |
| Narsim Kamath | High-Performance Computing |
| Cameron Kass | High-Performance Computing |

**DSA Mentors:** Dr. Ilker Ersoy and Dr. Timothy Haithcoat

**Subject Matter Experts:** Director Arvids Petersons (Missouri Medicaid Fraud Control Unit); Director Richard Ferrari, Darla Weekley, Colin Murdick, and Jeffrey Rex (Missouri Medicaid Audit and Compliance); Lucas Gallardo (Alivia Analytics)

---

## Abstract

Fraud is a pervasive and complex problem within the United States healthcare system, necessitating increasingly robust detection methods. This project integrates CMS Open Payments data, CMS DMEPOS program utilization data, and the HHS OIG List of Excluded Individuals/Entities into a standardized dataset from which interpretable, specialty-level fraud risk signals are extracted for providers in Missouri and bordering states during calendar years 2021–2023.

An explainable hybrid model pipeline using Isolation using Nearest Neighbor Ensemble (INNE) and XGBoost is applied to determine baseline "normal" behavior across the focused population, then flag providers with a higher estimated likelihood of fraud risk — without relying on large numbers of confirmed fraud labels. For transparency, each score is paired with its top contributing anomaly factors, enabling faster and more consistent investigative prioritization.

The final model delivered a **50x lift** over the fraud prevalence baseline and maintained a **10% confirmed fraud hit rate** among the top 100 flagged providers. Results are cross-referenced with Missouri's list of active Medicaid providers to identify overlaps with high-risk providers participating in the Medicare DMEPOS program.

Preliminary work: [Case Study: Fraud Detection in Healthcare (DMEPOS Analysis)](https://github.com/N4e-N4e/Fraud-Detection-in-Healthcare-DMEPOS-Analysis)

---

## Keywords
`Class Imbalance` `DMEPOS` `Fraud Detection` `Medicare` `XGBoost`

---

## Repository Structure

```
├── TeamArtifacts/                   # Sprint notebooks and source code
├── FinalDocumentation/              # Final report, IEEE publication and Infographic
├── Dashboard/                       # Final Tableau dashboard file
├── AI Assistant Documentation/      # Finalized architecture and usability scoring template
└── Metadata/                        # Dataset metadata files
```

---

## Final Deliverable

The project findings are delivered through an interactive dashboard built in Tableau, and an agentic AI assistant - **DEMIrobato** - that uses a Model Context Protocol (MCP) framework to access the HHS OIG and Missouri Secretary of State websites in real time, improving investigators' ability to access reports, audits, investigations, and oversight findings.

The AI assistant is split across three repositories:

| Component | Description | Link |
|---|---|---|
| Frontend | Plain HTML/CSS/JS chatbot UI hosted on GitHub Pages | [DMEPOS.github.io](https://github.com/N4e-N4e/DMEPOS.github.io) |
| Gemini Backend | FastAPI server powering the Gemini LLM and tool routing | [Gemini_Backend_site](https://github.com/N4e-N4e/Gemini_Backend_site) |
| MCP Backend | Web scraping tools for OIG and Missouri SOS via Selenium | [MCP_Backend_site](https://github.com/N4e-N4e/MCP_Backend_site) |

### The finalized and deployed web-based AI assistant: [DEMIrobato](https://n4e-n4e.github.io/DMEPOS.github.io/)

---

## Data Sources

All data used in this project is publicly available and was accessed directly from official government websites at no cost.

| Source | Description |
|---|---|
| CMS DMEPOS - By Referring Provider | Provider-level Medicare DMEPOS billing data (2021–2023) |
| CMS DMEPOS - By Referring Provider and Service | Service-level DMEPOS billing data (2021–2023) |
| CMS DMEPOS - By Supplier | Supplier-level DMEPOS billing data (2021–2023) |
| CMS Open Payments - General Payments | Financial relationships between manufacturers and providers |
| CMS Open Payments - Ownership Interests | Physician ownership interests in medical manufacturers |
| HHS OIG LEIE | List of excluded individuals and entities (fraud labels) |
| USDA RUCA Codes | Rural-urban classification by ZIP code |
| CMS Taxonomy Crosswalk | Provider specialty classification |
| Missouri Family Support Division | Active Missouri Medicaid providers |
| Missouri Secretary of State | Business entity registry (live, scraped in real time) |

---

## Storage and Infrastructure

All data processing and modeling was conducted across two environments:

- **DSA JupyterHub** - University of Missouri shared team environment
- **Hellbender HPC Cluster** - University of Missouri high-performance computing cluster (used for feature selection and large-scale modeling)

Source code for the AI assistant is version-controlled on GitHub and deployed via **Render**, which automatically deploys and updates backend servers on every push.

---

## Ethical Statement

All datasets are publicly available and used in accordance with their stated purposes of transparency and research. No patient-level identifiers were used at any stage. The project produces risk signals to assist human investigators in prioritizing cases for review - it does not issue fraud determinations. All final decisions remain with qualified subject matter experts.
