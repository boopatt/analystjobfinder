# Presentation Plan & Speaker Notes
**Job Finder Assistant — ISA 632 Group Project**
**Total time: ~10 minutes** (8 min slides · 2 min live demo on slide 14)

---

## Timing Overview

| # | Slide | Speaker | Time |
|---|-------|---------|------|
| 1 | Title | — | 15 sec |
| 2 | Agenda | — | 20 sec |
| 3 | Business Problem | Seth | 45 sec |
| 4 | Scope & Dataset | Seth | 40 sec |
| 5 | Building the Knowledge Base | Seth | 45 sec |
| 6 | End-to-End Architecture | Thenmozhi | 60 sec |
| 7 | Prompt Engineering Journey | Thenmozhi | 50 sec |
| 8 | Structured Output Formats | Thenmozhi | 30 sec |
| 9 | Model Registry & Deployment | Thenmozhi | 30 sec |
| 10 | Evaluation Design | Luke | 40 sec |
| 11 | Evaluation Results | Luke | 40 sec |
| 12 | Selected Question Results | Luke | 30 sec |
| 13 | Why We Did Not Fine-Tune | Luke | 35 sec |
| **14** | **Live Demo** | **Thenmozhi** | **2 min** |
| 15 | Key Lessons Learned | — | 25 sec |
| 16 | Thank You / Q&A | — | 10 sec |
| **Total** | | | **~10 min** |

---

## Speaker Notes

---

### Slide 1 — Title *(15 sec)*
*No speaker assigned — anyone can open.*

> "Good [morning/afternoon]. We're Group [X] from ISA 632, and today we're presenting the Job Finder Assistant — a GenAI chatbot that helps users search data engineering job listings using plain English, built on Databricks with RAG and LangChain."

---

### Slide 2 — Agenda *(20 sec)*
*No speaker assigned — Seth can lead into his section.*

> "We'll walk through the project in three parts. Seth covers the business problem and how we built the data pipeline. Thenmozhi covers the agent architecture, prompt engineering, and deployment. Luke covers how we evaluated the system. We'll close with a live demo."

---

### Slide 3 — Business Problem *(45 sec)* · **Seth**

> "The problem we're solving is straightforward: job seekers waste hours manually scanning postings across multiple sites, and generic keyword search tools return results that don't match what the person actually asked for — wrong seniority level, wrong location, wrong skills.
>
> Our solution is a conversational chatbot. You type in plain English — 'show me senior data engineering roles at Deloitte' — and it retrieves real, structured results from a curated database. Crucially, when no match exists, it tells you clearly instead of making something up."

---

### Slide 4 — Scope & Dataset *(40 sec)* · **Seth**

> "We scoped the project to data engineering and data analyst roles from three companies: Deloitte, JPMorgan Chase, and Amazon. That's about 35 real job listing PDFs covering mid-to-senior level positions.
>
> The core design principle from the project brief — and one we took seriously — is that a generic LLM alone is not enough. The model needs to be connected to current, relevant data through RAG, and the responses need to be evaluated, not assumed to be correct."

---

### Slide 5 — Building the Knowledge Base *(45 sec)* · **Seth**

> "The data pipeline in Notebook 01 has four steps. We start with raw job PDFs stored in a Unity Catalog Volume. We parse them using Databricks' built-in `ai_parse_document()` function — no custom PDF parsing code. The extracted text gets flattened into rows and written to a Delta table called `jobs_knowledge_base`, with Change Data Feed enabled, which is required for the Vector Search sync to work.
>
> We chose Vector Search because it gives us semantic similarity — users don't need to match exact keywords. If they say 'roles involving data pipelines,' it finds postings about ETL and Spark even without those exact words. And it automatically stays in sync when we update the Delta table."

---

### Slide 6 — End-to-End Architecture *(60 sec)* · **Thenmozhi**

> "Here's how the full system works. There are two separate paths.
>
> The **query path**: a user types a question in the Streamlit UI. That goes to the Model Serving endpoint on Databricks, which invokes our LangChain agent — just one agent, with one tool: the jobindex VectorSearchRetrieverTool. The agent passes the query to Llama 4 Maverick with our routing prompt, which decides whether to call the retriever or answer from its own knowledge. The response comes back to Streamlit.
>
> The **feedback path** is completely separate: when a user clicks 👍 or 👎, the Streamlit app calls the SQL Statement Execution API directly and writes to a Delta table called `chatbot_feedback`. The agent is not involved at all.
>
> We deliberately chose a single-agent, single-tool architecture. No multi-agent orchestration, no MCP. Our goal is narrowly scoped — retrieve from one indexed source — and adding complexity would only create more failure points."

---

### Slide 7 — Prompt Engineering Journey *(50 sec)* · **Thenmozhi**

> "Getting the prompt right was the most iterative part of the project. The original prompt had five failure modes we diagnosed using Databricks Genie.
>
> It hallucinated search keywords that the user never mentioned. It called a tool by a hardcoded name that didn't match the auto-generated name from the Vector Search index. It returned wrong seniority levels without flagging the mismatch. And it called the retriever even for completely general questions like 'What is Python?' — unnecessary and slow.
>
> The improved prompt adds a routing layer at the top: the agent first classifies whether the question is job-related or general knowledge, and only calls the retriever for job queries. Then five explicit rules cover how to query the tool, how to verify results, and what to do when the results don't match."

---

### Slide 8 — Structured Output Formats *(30 sec)* · **Thenmozhi**

> "The prompt defines two output formats. When the retrieved results match what the user asked for, the agent returns a structured job posting: title, company, description, qualifications, and salary — all pulled from the retrieved documents, nothing fabricated.
>
> When there's no match — for example, the user asks for entry-level roles but the database only has senior ones — the agent uses the MISMATCH FORMAT. It explicitly says it couldn't find what was asked, shows what is available instead, and asks if the user wants to adjust. This transparency was a deliberate design choice."

---

### Slide 9 — Model Registry & Deployment *(30 sec)* · **Thenmozhi**

> "Once the agent was working, we logged it to MLflow, registered it to Unity Catalog, and deployed it using `agents.deploy()` with `scale_to_zero=True` to keep costs low. The Vector Search index is declared as a resource dependency so it's automatically provisioned when the endpoint starts.
>
> The Streamlit app runs on Databricks Apps — no separate server needed. Users see suggested prompt buttons on first load, and every assistant response has thumbs up/down buttons that feed into our feedback Delta table."

---

### Slide 10 — Evaluation Design *(40 sec)* · **Luke**

> "For evaluation, we used `mlflow.genai.evaluate()` from MLflow 3.0, which uses an LLM as a judge to score each response against natural-language rubrics.
>
> We wrote 12 test questions that cover the full realistic range: role-specific searches, multi-criteria filtering, salary questions, and out-of-scope requests. We used four scorers — two built-in MLflow ones for relevance and safety, and two custom ones we wrote specifically for this project.
>
> The custom scorers matter because generic scorers can't catch domain-specific failures. `job_relevant` checks that responses cite real postings. `filter_aware` checks that when the user specifies a filter — location, seniority, skills — the response explicitly acknowledges it."

---

### Slide 11 — Evaluation Results *(40 sec)* · **Luke**

> "The results were mostly strong. Safety was 100% — no harmful content anywhere. Job Relevant and Relevance to Query were both 92%, meaning 11 of 12 responses were grounded in real postings and actually addressed what was asked.
>
> The outlier was Filter Aware at 58%. Five of our 12 questions failed on filter constraints. And after drilling into those 5 failures, we found they all shared the exact same root cause — which brings us to the next slide."

---

### Slide 12 — Selected Question Results *(30 sec)* · **Luke**

> "You can see the pattern clearly in the table. Q2 — beginner data analyst in New York, Python only — fails Filter Aware. Q11 — most needed skill for beginner level — fails both scorers. Q12 — years of experience for a beginner — fails Filter Aware. All five failures involve entry-level or multi-criteria queries.
>
> Every single filter-aware failure has the same root cause: our database contains no junior or beginner-level job postings. The model was actually behaving correctly — it was honestly flagging mismatches — but the data wasn't there to satisfy the queries."

---

### Slide 13 — Why We Did Not Fine-Tune *(35 sec)* · **Luke**

> "We explicitly considered fine-tuning and decided against it. Fine-tuning changes how a model responds — it doesn't change what it knows. Our problem was a data gap, not a behavior gap.
>
> The right fixes are in the data layer: add entry-level job postings, add metadata fields for structured filtering, and use hybrid search that combines semantic similarity with hard filters. These stay within the RAG architecture that's already working well. Fine-tuning 30 PDFs into a model like Llama 4 Maverick would take significant GPU resources and produce stale results the moment the listings change."

---

### Slide 14 — Live Demo *(2 minutes)* · **Thenmozhi**

> "Let me show you the chatbot. I'll open the Streamlit app now."

**Demo script — 5 prompts in 2 minutes:**

| # | Prompt | What to say |
|---|--------|-------------|
| 1 | *"Show me senior data engineering roles at Deloitte"* | "Happy path — retrieves a real posting with title, description, and salary." |
| 2 | *"What are the salary ranges for data engineering roles at JPMorgan Chase?"* | "Factual salary lookup — comes directly from the indexed documents." |
| 3 | *"Find data engineering jobs that require Python and SQL"* | "Semantic search — doesn't need exact keywords in the posting." |
| 4 | *"What entry-level positions are available?"* | "This triggers the MISMATCH FORMAT — watch how the agent is honest about what it can't find." |
| 5 | *"What is Python?"* | "General knowledge routing — no retriever call, answers directly from the LLM." |

After prompt 4 or 5, click **👎** on one response to show the feedback form: select a category, add a comment, and click Submit. Say:

> "Feedback is collected per response. The rating, category, and comment go straight to a Delta table — completely separate from the agent — giving us labeled data for future improvements."

---

### Slide 15 — Key Lessons Learned *(25 sec)*
*No speaker assigned — anyone wrapping up.*

> "Three things we'd take to any future GenAI project: RAG grounding matters more than model size for factual accuracy. Prompt engineering has a higher return than fine-tuning for structured tasks like this. And evaluation has to be domain-specific — generic scorers would have missed the filter-aware failures entirely and given us a misleadingly high score."

---

### Slide 16 — Thank You *(10 sec)*

> "Thanks for your time. We're happy to take questions."

---

## Demo Prep Checklist

- [ ] Streamlit app is open in browser before presentation starts
- [ ] Databricks serving endpoint is warm (send a test query 5 min before)
- [ ] Confirm `DATABRICKS_TOKEN` is set in the app environment
- [ ] Clear the chat history before the demo (use the 🗑️ Clear button)
- [ ] Know which browser tab has the app — minimize distractions
