import streamlit as st
import requests
import os

# --- Configuration ---
SERVING_ENDPOINT_URL = os.environ.get("SERVING_ENDPOINT_URL", "")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

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


# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

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
        st.rerun()
