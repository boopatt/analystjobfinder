# Job Finder Assistant

A Retrieval-Augmented Generation (RAG) chatbot that helps users search job listings using natural language. Built on Databricks using LangChain, Llama 4 Maverick, and Vector Search, deployed as a Streamlit web application.

**Course:** ISA 632 — Miami University  
**Instructor:** Jay Shan  
**Team:** Thenmozhi Boopathy, Seth Grace, Luke Johnson

---

## Overview

Users type natural language queries (e.g., "Show me remote managerial data analyst roles") and the chatbot retrieves relevant job postings from a Vector Search index, verifies the results match the user's criteria, and formats a structured response. When no matching listings exist, it explicitly states the mismatch and shows what is available instead.

---

## Architecture

```
Raw Job PDFs (Unity Catalog Volume)
        ↓
ai_parse_document() → flatten text → Delta Table (jobs_knowledge_base)
        ↓
Vector Search Index (isa632_7474656346303369.boopatt.jobindex)
        ↓
LangChain Agent (Llama 4 Maverick + VectorSearchRetrieverTool)
        ↓
MLflow Model Registry → Databricks Model Serving Endpoint
        ↓
Streamlit App (chatbot_app/) → User with feedback collection (👍/👎)
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
├── 01_DataPreparation.ipynb       # Ingest PDFs → Delta table → Vector Search index
├── 02_AgentDevelopment.ipynb      # Build, prompt-engineer, register, and deploy agent
├── 03_Evaluation.ipynb            # MLflow evaluation with custom Guidelines scorers
├── 04_ChatbotDeployment.ipynb     # Verify endpoint, create feedback table, deploy app
├── agent.py                       # Core RAG agent (LangChain + MLflow ResponsesAgent)
├── eval_data.jsonl                # 12 evaluation questions with expected scorer criteria
├── ChatTesting.md                 # Informal early testing notes (pre-prompt engineering)
├── ChatTestingInference.md        # Formal inference breakdown of all 12 test questions
└── chatbot_app/
    ├── app.py                     # Streamlit UI with chat history and feedback collection
    ├── app.yaml                   # Databricks Apps deployment config
    └── requirements.txt           # streamlit, requests
```

---

## Notebooks

### 01 — Data Preparation
Reads raw job listing PDFs from a Unity Catalog Volume, parses them with `ai_parse_document()`, flattens the extracted elements into plain text, and writes them to a Delta table with Change Data Feed enabled. The Vector Search index is then synced and verified with a sample similarity search.

### 02 — Agent Development
Builds the LangChain tool-calling agent and documents the prompt engineering process. The original prompt caused hallucinated search keywords, tool name mismatches, and wrong seniority-level results. The improved prompt adds five explicit rules:

1. Always call the retriever tool before responding
2. Use the user's exact words as the search query
3. Base the response only on retrieved documents
4. After retrieval, verify the results match the user's stated criteria
5. If there is a mismatch, use the MISMATCH FORMAT instead of presenting wrong results

The agent is logged to MLflow, registered in Unity Catalog, and deployed with `agents.deploy()`.

### 03 — Evaluation
Runs `mlflow.genai.evaluate()` on 12 realistic test questions using four scorers:

| Scorer | Score | Notes |
|--------|-------|-------|
| Safety | 100% | No harmful content |
| Job Relevant | 92% | 11/12 grounded in actual postings |
| Relevance to Query | 92% | |
| Filter Aware | 58% | Main bottleneck — no entry-level postings in database |

The low Filter Aware score was diagnosed as a **data gap** (no junior/beginner listings), not a model capability gap. Fine-tuning was ruled out; the recommended fix is to expand the dataset with entry-level job postings and add metadata-based hybrid search.

### 04 — Chatbot Deployment
Verifies the serving endpoint with a live test query, creates the `chatbot_feedback` Delta table, and deploys the Streamlit app to Databricks Apps.

---

## Agent (`agent.py`)

| Component | Details |
|-----------|---------|
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

---

## Databricks Resources

| Resource | Name |
|----------|------|
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
|-------|-----------|----------------|
| Filter Aware score 58% | No entry-level postings in database | Add junior/beginner job listings |
| Response truncation on long answers | `max_tokens=500` too low | Increase to 1000+ in `agent.py` |
| Multi-criteria filtering failures | Semantic search can't enforce structured constraints | Add metadata fields + hybrid search |

---

## Tech Stack

- **Platform:** Databricks (Unity Catalog, Vector Search, Model Serving, Apps)
- **LLM:** Databricks Llama 4 Maverick
- **Agent framework:** LangChain + MLflow
- **UI:** Streamlit
- **Data format:** Delta tables with Change Data Feed
- **Document parsing:** Databricks `ai_parse_document()`
