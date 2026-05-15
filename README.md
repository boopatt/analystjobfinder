# Job Finder Assistant

A Retrieval-Augmented Generation (RAG) chatbot that helps users search job listings using natural language. Built on Databricks using LangChain, Llama 4 Maverick, and Vector Search, deployed publicly as a Streamlit web application.

**Course:** ISA 632 — Miami University  
**Instructor:** Jay Shan  
**Team:** Thenmozhi Boopathy, Seth Grace, Luke Johnson

---

## Live App

| Deployment | URL | Access |
|---|---|---|
| Streamlit Community Cloud | [analystjobfinder.streamlit.app](https://analystjobfinder.streamlit.app/) | Public — no login needed |
| Databricks Apps | [job-finder-chatbot-7474656346303369.aws.databricksapps.com](https://job-finder-chatbot-7474656346303369.aws.databricksapps.com) | Workspace users only |

---

## Overview

Users type natural language queries (e.g., "Show me remote managerial data analyst roles") and the chatbot retrieves relevant job postings from a Vector Search index, verifies the results match the user's criteria, and formats a structured response. When no matching listings exist, it explicitly states the mismatch and shows what is available instead.

The knowledge base combines **37 curated job listing PDFs** (Deloitte, JPMorgan Chase, Amazon) with **2,530 scraped Data Engineer roles** from a CSV dataset, giving the system broad coverage across companies and seniority levels.

---

## Architecture

```
Raw Job PDFs (37 files, Unity Catalog Volume)      CSV Dataset (2,530 roles, DataEngineer.csv)
        ↓                                                   ↓
ai_parse_document() → flatten text              Spark transform → concat fields
        ↓                                                   ↓
        └──────────────────┬────────────────────────────────┘
                           ↓
              Delta Table (jobs_knowledge_base)
                           ↓
       Vector Search Index (boopatt.jobindex)
                           ↓
    LangChain Agent (Llama 4 Maverick + VectorSearchRetrieverTool)
                           ↓
    MLflow Model Registry → Databricks Model Serving Endpoint
                           ↓
    Streamlit App (chatbot_app/) → User + feedback collection (👍/👎)
```

**Runtime query flow:**
1. User submits query in Streamlit UI
2. App POSTs to Model Serving endpoint
3. Agent calls Vector Search retriever tool with the user's exact words
4. LLM verifies retrieved results match user's seniority, function, and location criteria
5. Returns a formatted job listing or a MISMATCH response explaining what was found instead
6. User feedback (rating + optional category/comment) is stored in a Delta table

---

## Project Structure

```
analystjobfinder/
├── 01_DataPreparation.ipynb       # Ingest PDFs + CSV → Delta table → Vector Search index
├── 02_AgentDevelopment.ipynb      # Build, prompt-engineer, register, and deploy agent
├── 03_Evaluation.ipynb            # MLflow evaluation with custom Guidelines scorers
├── 04_ChatbotDeployment.ipynb     # Verify endpoint, create feedback table, deploy app
├── agent.py                       # Core RAG agent (LangChain + MLflow ResponsesAgent)
├── eval_data.jsonl                # 12 evaluation questions with expected scorer criteria
├── ChatTesting.md                 # Informal early testing notes (pre-prompt engineering)
├── ChatTestingInference.md        # Formal inference breakdown of all 12 test questions
├── presentation.html              # Slide deck (18 slides, self-contained HTML)
└── chatbot_app/
    ├── app.py                     # Streamlit UI with chat history and feedback collection
    ├── app.yaml                   # Databricks Apps deployment config
    └── requirements.txt           # streamlit, requests
```

---

## Notebooks

### 01 — Data Preparation
Reads raw job listing PDFs from a Unity Catalog Volume, parses them with `ai_parse_document()`, and flattens the extracted elements into plain text rows. In a second step, a CSV file containing 2,530 scraped Data Engineer roles is processed using a Spark transformation — concatenating job title, company, location, and description into a single content string per row. Both sources are written to the same Delta table (`jobs_knowledge_base`) with Change Data Feed enabled. The Vector Search index is then synced and verified with a sample similarity search.

### 02 — Agent Development
Builds the LangChain tool-calling agent and documents the prompt engineering process. The original prompt caused hallucinated search keywords, tool name mismatches, and wrong seniority-level results. The improved prompt adds a routing layer and five explicit rules:

1. Always call the retriever tool before responding
2. Use the user's exact words as the search query
3. Base the response only on retrieved documents
4. After retrieval, verify the results match the user's stated criteria
5. If there is a mismatch, use the MISMATCH FORMAT instead of presenting wrong results

The agent is logged to MLflow, registered in Unity Catalog, and deployed with `agents.deploy()`.

### 03 — Evaluation
Runs `mlflow.genai.evaluate()` on 12 realistic test questions using four scorers. The evaluation was run twice — once on the original PDF-only dataset and again after the CSV expansion.

| Scorer | PDF-only (Run 1) | PDF + CSV (Run 2) | Notes |
|---|---|---|---|
| Safety | 100% | 100% | Unchanged |
| Job Relevant | 92% | 50% | CSV rows introduced retrieval noise |
| Relevance to Query | 92% | 67% | Same root cause |
| Filter Aware | 58% | 67% ↑ | CSV addressed entry-level data gap |

The Filter Aware improvement confirms the CSV expansion helped coverage. The drop in Job Relevant and Relevance to Query shows that adding less-curated data without structured filtering reduces retrieval precision. The recommended fix is hybrid search — combining semantic similarity with metadata filters on seniority, location, and required skills.

### 04 — Chatbot Deployment
Verifies the serving endpoint with a live test query, creates the `chatbot_feedback` Delta table, and deploys the Streamlit app to two targets:
- **Databricks Apps** — internal deployment for workspace users
- **Streamlit Community Cloud** — public deployment via GitHub, accessible at [analystjobfinder.streamlit.app](https://analystjobfinder.streamlit.app/). Auto-redeploys on every `git push` to `main`.

---

## Agent (`agent.py`)

| Component | Details |
|---|---|
| LLM | `ChatDatabricks` — `databricks-llama-4-maverick`, max_tokens=500, temp=0.5 |
| Retriever | `VectorSearchRetrieverTool` on `isa632_7474656346303369.boopatt.jobindex` |
| Agent type | LangChain `create_tool_calling_agent` + `AgentExecutor` |
| Framework | MLflow `ResponsesAgent` wrapper for Databricks serving compatibility |

---

## Streamlit App (`chatbot_app/app.py`)

- Chat history preserved in session state across turns
- Each assistant message shows thumbs up/down feedback buttons
- On rating, an optional form appears for category (7 options) and free-text comment
- Ratings and comments are written to `isa632_7474656346303369.boopatt.chatbot_feedback` via the SQL Statement Execution API

**User Feedback to date:** 18 responses rated — 16 👍 positive (89%), 2 👎 negative.

---

## Databricks Resources

| Resource | Name |
|---|---|
| Catalog / Schema | `isa632_7474656346303369` / `boopatt` |
| Knowledge base table | `jobs_knowledge_base` |
| Feedback table | `chatbot_feedback` |
| Vector Search index | `isa632_7474656346303369.boopatt.jobindex` |
| Model registry | `isa632_7474656346303369.boopatt.getstarted_job_listings` |
| Serving endpoint | `agents_isa632_7474656346303369-boopatt-job_finder` |
| Databricks host | `https://dbc-0726d26f-3749.cloud.databricks.com` |

---

## Evaluation Dataset

`eval_data.jsonl` contains 12 questions covering:
- Role-specific searches (visa sponsorship, remote work, managerial, AI-focused)
- Multi-criteria filtering (location + level + skill)
- Out-of-scope queries (images, company culture)
- Salary and experience-level questions

---

## Known Limitations

| Issue | Root Cause | Recommended Fix |
|---|---|---|
| Job Relevant / Relevance dropped after CSV | Less-curated CSV rows introduce retrieval noise | Hybrid search with metadata filters |
| Count queries unsupported ("How many Deloitte jobs?") | Vector Search has no aggregation capability | Add SQL Statement Execution tool to agent |
| Multi-criteria filtering failures | Semantic search can't enforce structured constraints | Add metadata fields + hybrid search |
| Response truncation on long answers | `max_tokens=500` too low | Increase to 1000+ in `agent.py` |

---

## Tech Stack

- **Platform:** Databricks (Unity Catalog, Vector Search, Model Serving, Apps)
- **LLM:** Databricks Llama 4 Maverick
- **Agent framework:** LangChain + MLflow
- **UI:** Streamlit
- **Hosting:** Streamlit Community Cloud ([analystjobfinder.streamlit.app](https://analystjobfinder.streamlit.app/))
- **Source:** [github.com/boopatt/analystjobfinder](https://github.com/boopatt/analystjobfinder)
- **Data format:** Delta tables with Change Data Feed
- **Document parsing:** Databricks `ai_parse_document()`
