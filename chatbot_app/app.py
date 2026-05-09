import streamlit as st
import requests
import os
from datetime import datetime

# --- Configuration ---
SERVING_ENDPOINT_URL = os.environ.get(
    "SERVING_ENDPOINT_URL",
    "https://dbc-0726d26f-3749.cloud.databricks.com/serving-endpoints/agents_isa632_7474656346303369-boopatt-getstarted_job_listings/invocations"
)
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")
DATABRICKS_HOST = os.environ.get(
    "DATABRICKS_HOST",
    "https://dbc-0726d26f-3749.cloud.databricks.com"
)
# SQL warehouse HTTP path for feedback storage
SQL_WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "")
# Fully qualified table for storing feedback
FEEDBACK_TABLE = os.environ.get(
    "FEEDBACK_TABLE",
    "isa632_7474656346303369.boopatt.chatbot_feedback"
)

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
    page_title="Job Listings Chatbot",
    page_icon="💼",
    layout="centered"
)

st.title("💼 Job Listings Assistant")
st.caption("Ask me about available job positions — I'll search our database and provide relevant listings.")

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}
if "pending_feedback" not in st.session_state:
    st.session_state.pending_feedback = None  # Tracks which message is showing the feedback form


def call_agent(user_message: str) -> str:
    """Call the agent serving endpoint and return the response text."""
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
        response.raise_for_status()
        result = response.json()

        # Extract text from Responses API format
        output = result.get("output", [])
        if output and len(output) > 0:
            content = output[0].get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "No response received.")
        return "No response received from the agent."

    except requests.exceptions.Timeout:
        return "⏱️ The request timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        return f"❌ Error: {e.response.status_code} - {e.response.text[:200]}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"


def submit_feedback(question: str, response: str, rating: str, category: str = "", comment: str = ""):
    """Write user feedback to a Delta table via the SQL Statement Execution API."""
    if not SQL_WAREHOUSE_ID or not DATABRICKS_TOKEN:
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
        return resp.status_code == 200
    except Exception:
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

# --- Chat Input ---
if prompt := st.chat_input("Ask about available jobs (e.g., 'Show me data engineering roles')"):
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
        "This chatbot searches our job listings database and provides "
        "relevant position summaries. It will let you know if your "
        "specific criteria (seniority level, domain, etc.) don't match "
        "available roles."
    )
    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.feedback_given = {}
        st.session_state.pending_feedback = None
        st.rerun()
