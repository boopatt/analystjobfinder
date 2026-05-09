import streamlit as st
import requests
import os
import time
from datetime import datetime

# --- Configuration ---
DATABRICKS_HOST = os.environ.get(
    "DATABRICKS_HOST",
    "https://dbc-0726d26f-3749.cloud.databricks.com"
)
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

ENDPOINT_NAME = os.environ.get(
    "ENDPOINT_NAME",
    "agents_isa632_7474656346303369-boopatt-job_finder"
)
SERVING_ENDPOINT_URL = "https://dbc-0726d26f-3749.cloud.databricks.com/serving-endpoints/agents_isa632_7474656346303369-boopatt-job_finder/invocations"
# SQL warehouse HTTP path for feedback storage
SQL_WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "1c9c842c6ceae014")
# Fully qualified table for storing feedback
FEEDBACK_TABLE = os.environ.get(
    "FEEDBACK_TABLE",
    "isa632_7474656346303369.boopatt.chatbot_feedback"
)

# --- Startup Diagnostics ---
print("=" * 60)
print("APP STARTUP DIAGNOSTICS")
print(f"  DATABRICKS_HOST: {DATABRICKS_HOST}")
print(f"  DATABRICKS_TOKEN set: {bool(DATABRICKS_TOKEN)} (length: {len(DATABRICKS_TOKEN)})")
print(f"  ENDPOINT_NAME: {ENDPOINT_NAME}")
print(f"  SERVING_ENDPOINT_URL: {SERVING_ENDPOINT_URL}")
print(f"  SQL_WAREHOUSE_ID: {SQL_WAREHOUSE_ID}")
print(f"  FEEDBACK_TABLE: {FEEDBACK_TABLE}")
print("=" * 60)

# Feedback category options (similar to Review App)
FEEDBACK_CATEGORIES = [
    "Accurate & helpful",
    "Incorrect information",
    "Incomplete answer",
    "Not relevant to question",
    "Too verbose",
    "Formatting issues",
    "Other",
]

# --- Page Config ---
st.set_page_config(
    page_title="Job Finder Assistant",
    page_icon="💼",
    layout="centered"
)

st.title("💼 Job Finder Assistant")
st.caption("Ask in plain English about any data engineering role — I'll search open positions from Deloitte, JPMorgan Chase, and Amazon and return structured summaries with job descriptions, qualifications, and salary ranges, or let you know clearly when no match is found.")

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}
if "pending_feedback" not in st.session_state:
    st.session_state.pending_feedback = None  # Tracks which message is showing the feedback form
if "queued_prompt" not in st.session_state:
    st.session_state.queued_prompt = None


def call_agent(user_message: str) -> str:
    """Call the agent serving endpoint and return the response text."""
    print(f"[call_agent] Sending query: {user_message[:100]}...")
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": [
            {"role": "user", "content": user_message}
        ]
    }

    try:
        response = requests.post(SERVING_ENDPOINT_URL, headers=headers, json=payload, timeout=60)
        print(f"[call_agent] Response status: {response.status_code}")
        response.raise_for_status()
        result = response.json()

        # Extract text from Responses API format
        output = result.get("output", [])
        if output and len(output) > 0:
            content = output[0].get("content", [])
            if content and len(content) > 0:
                text = content[0].get("text", "No response received.")
                print(f"[call_agent] Success - response length: {len(text)}")
                return text
        print("[call_agent] No output in response")
        return "No response received from the agent."

    except requests.exceptions.Timeout:
        print("[call_agent] TIMEOUT")
        return "⏱️ The request timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        print(f"[call_agent] HTTP ERROR: {e.response.status_code} - {e.response.text[:200]}")
        return f"❌ Error: {e.response.status_code} - {e.response.text[:200]}"
    except Exception as e:
        print(f"[call_agent] EXCEPTION: {type(e).__name__}: {str(e)}")
        return f"❌ Unexpected error: {str(e)}"


def submit_feedback(question: str, response: str, rating: str, category: str = "", comment: str = ""):
    """Write user feedback to a Delta table via the SQL Statement Execution API."""
    print(f"[submit_feedback] Called with rating={rating}, category={category}")
    print(f"[submit_feedback] SQL_WAREHOUSE_ID={SQL_WAREHOUSE_ID}, TOKEN set={bool(DATABRICKS_TOKEN)}")

    if not SQL_WAREHOUSE_ID:
        print("[submit_feedback] SKIPPED - no SQL_WAREHOUSE_ID")
        st.toast("⚠️ Feedback not saved — no SQL warehouse configured", icon="⚠️")
        return False

    if not DATABRICKS_TOKEN:
        print("[submit_feedback] SKIPPED - no DATABRICKS_TOKEN")
        st.toast("⚠️ Feedback not saved — no auth token available", icon="⚠️")
        return False

    # Escape single quotes in strings for SQL
    question_escaped = question.replace("'", "''")
    response_escaped = response.replace("'", "''")[:1000]  # Truncate long responses
    category_escaped = category.replace("'", "''")
    comment_escaped = comment.replace("'", "''")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    sql = f"""
    INSERT INTO {FEEDBACK_TABLE} (timestamp, question, response, rating, category, comment)
    VALUES ('{timestamp}', '{question_escaped}', '{response_escaped}', '{rating}', '{category_escaped}', '{comment_escaped}')
    """
    print(f"[submit_feedback] SQL: {sql[:200]}...")

    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "warehouse_id": SQL_WAREHOUSE_ID,
        "statement": sql,
        "wait_timeout": "10s",
    }

    try:
        resp = requests.post(
            f"{DATABRICKS_HOST}/api/2.0/sql/statements",
            headers=headers,
            json=payload,
            timeout=15,
        )
        print(f"[submit_feedback] Response status: {resp.status_code}")
        print(f"[submit_feedback] Response body: {resp.text[:300]}")

        if resp.status_code == 200:
            st.toast("✅ Feedback saved successfully!", icon="✅")
            return True
        else:
            st.toast(f"❌ Feedback failed: {resp.status_code} - {resp.text[:100]}", icon="❌")
            return False
    except Exception as e:
        print(f"[submit_feedback] EXCEPTION: {type(e).__name__}: {str(e)}")
        st.toast(f"❌ Feedback error: {str(e)[:100]}", icon="❌")
        return False


# --- Display Chat History with Feedback ---
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Show feedback buttons for assistant messages
        if message["role"] == "assistant":
            feedback_key = f"feedback_{idx}"

            if feedback_key not in st.session_state.feedback_given:
                col1, col2, col3 = st.columns([1, 1, 10])
                with col1:
                    if st.button("👍", key=f"up_{idx}", help="Good response"):
                        st.session_state.pending_feedback = {"idx": idx, "rating": "positive"}
                        st.rerun()
                with col2:
                    if st.button("👎", key=f"down_{idx}", help="Needs improvement"):
                        st.session_state.pending_feedback = {"idx": idx, "rating": "negative"}
                        st.rerun()

                # Show expanded feedback form if this message is pending
                if (
                    st.session_state.pending_feedback
                    and st.session_state.pending_feedback["idx"] == idx
                ):
                    pending = st.session_state.pending_feedback
                    rating_emoji = "👍" if pending["rating"] == "positive" else "👎"

                    st.divider()
                    st.markdown(f"**{rating_emoji} Tell us more** *(optional)*")

                    category = st.selectbox(
                        "Category",
                        options=["— Select —"] + FEEDBACK_CATEGORIES,
                        key=f"cat_{idx}",
                    )
                    comment = st.text_area(
                        "Additional comments",
                        placeholder="What was good or what could be improved?",
                        max_chars=500,
                        key=f"comment_{idx}",
                    )

                    col_submit, col_skip = st.columns(2)
                    with col_submit:
                        if st.button("Submit feedback", key=f"submit_{idx}", type="primary"):
                            question = st.session_state.messages[idx - 1]["content"] if idx > 0 else ""
                            selected_category = category if category != "— Select —" else ""
                            submit_feedback(
                                question, message["content"],
                                pending["rating"], selected_category, comment
                            )
                            st.session_state.feedback_given[feedback_key] = pending["rating"]
                            st.session_state.pending_feedback = None
                            st.rerun()
                    with col_skip:
                        if st.button("Skip", key=f"skip_{idx}"):
                            question = st.session_state.messages[idx - 1]["content"] if idx > 0 else ""
                            submit_feedback(
                                question, message["content"],
                                pending["rating"]
                            )
                            st.session_state.feedback_given[feedback_key] = pending["rating"]
                            st.session_state.pending_feedback = None
                            st.rerun()
            else:
                rating = st.session_state.feedback_given[feedback_key]
                st.caption(f"{'👍' if rating == 'positive' else '👎'} Feedback recorded — thank you!")

# --- Suggested Prompts ---
if not st.session_state.messages:
    st.markdown("**Try asking:**")
    suggestions = [
        "Show me data engineering roles at Amazon",
        "What senior data engineer positions are available at Deloitte?",
        "Find data engineering jobs that require Python and SQL",
        "What are the salary ranges for data engineering roles at JPMorgan Chase?",
    ]
    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        if cols[i % 2].button(suggestion, use_container_width=True):
            st.session_state.queued_prompt = suggestion
            st.rerun()

# --- Chat Input ---
prompt = st.chat_input("Ask about available jobs (e.g., 'Show me data engineering roles at Amazon')")
if not prompt and st.session_state.queued_prompt:
    prompt = st.session_state.queued_prompt
    st.session_state.queued_prompt = None

if prompt:
    # Add user message to history and display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Searching job listings..."):
            response_text = call_agent(prompt)
        st.markdown(response_text)

    # Add assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.rerun()

# --- Sidebar ---
with st.sidebar:
    st.header("About")
    st.markdown(
        "**Job Finder Assistant**\n\n"
        "A GenAI chatbot built on Databricks that helps job seekers quickly "
        "discover relevant positions — saving hours of manual search by "
        "matching your criteria (role, seniority, location, skills) against "
        "our curated job listings database in seconds.\n\n"
        "**Course:** ISA 632 — Miami University\n\n"
        "**Instructor:** Jay Shan\n\n"
        "**Team**\n"
        "- Thenmozhi Boopathy\n"
        "- Seth Grace\n"
        "- Luke Johnson"
    )
    st.divider()
    st.markdown(
        "**Help us improve!**\n\n"
        "After each response, use the 👍 / 👎 buttons to rate the answer. "
        "Your feedback helps us make the bot more accurate and useful."
    )
    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.feedback_given = {}
        st.session_state.pending_feedback = None
        st.rerun()
