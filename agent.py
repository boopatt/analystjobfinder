import os
import mlflow
from uuid import uuid4
from typing import Any, List, Dict

from mlflow.pyfunc import ResponsesAgent
from mlflow.entities import SpanType
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from databricks_langchain import ChatDatabricks, VectorSearchRetrieverTool


def build_agent() -> AgentExecutor:
    # LLM endpoint
    llm = ChatDatabricks(
        endpoint=os.environ.get("LLM_ENDPOINT_NAME", "databricks-llama-4-maverick"),
        max_tokens=500,
        temperature=0.5,
    )

    # Read env for VS index (set this in your logging/serving env)
    vs_index_name = os.environ.get("VS_INDEX_NAME")
    if not vs_index_name:
        raise RuntimeError("VS_INDEX_NAME is not set in environment")

    # Tools
    # Note: VectorSearchRetrieverTool auto-generates tool name from the index name
    # (dots replaced with double underscores), so we derive it here for the prompt.
    tool_name = vs_index_name.replace(".", "__")
    retriever_tool = VectorSearchRetrieverTool(
        index_name=vs_index_name,
        description=(
            "Use to find relevant passages about jobs, description and examples. "
            "Input should be a natural-language question or keywords."
        ),
    )
    uc_tools: List[Any] = []  # add UC tools here if you use them

    # Prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            (
            "system",
            f"""You are a job description assistant. Your ONLY data source is the {tool_name} retriever tool.

CRITICAL RULES:
1. ALWAYS call {tool_name} before responding. Never answer from your own knowledge.
2. When calling the tool, use the user's EXACT words or a close paraphrase as the query. Do NOT invent job titles, companies, or keywords the user did not mention. If the user's request is broad (e.g., "show me available roles"), use a general query like "available jobs" or "job openings".
3. Base your response ONLY on the documents returned by the tool. Do not add requirements, qualifications, or details that are not in the retrieved text.
4. AFTER retrieving results, you MUST verify whether the results actually match the user's request. Specifically check:
   - Seniority level: Does the user want "entry level"/"junior" but you found "Manager"/"Senior"/"Lead"/"Director" roles? That is a MISMATCH.
   - Job function: Does the user want "marketing" but you found "engineering" roles? That is a MISMATCH.
   - Any other explicit criteria the user mentioned (location, industry, etc.).
5. If there is a mismatch, you MUST NOT present the results as if they satisfy the request. Instead, respond with the MISMATCH FORMAT below.

OUTPUT FORMAT when results MATCH the user's request:
Title: <exact or closely paraphrased title from the retrieved job posting>

Job Description: <250-word summary using only facts from the retrieved documents. Include role, key responsibilities, qualifications, and compensation if present in the source.>

MISMATCH FORMAT when results do NOT match the user's request:
I was unable to find any [user's criteria, e.g., "entry-level"] positions in our current job database. The available roles are at a different seniority level.

Here is what is currently available:
Title: <actual title from retrieved posting>
Level: <actual seniority level, e.g., Manager, Senior, Consultant>
Brief Summary: <2-3 sentence description of the role>

Would you like more details about any of these roles, or would you like to adjust your search criteria?"""
            ),
            MessagesPlaceholder("chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    agent_chain = create_tool_calling_agent(
        llm=llm, tools=[retriever_tool, *uc_tools], prompt=prompt
    )
    return AgentExecutor(agent=agent_chain, tools=[retriever_tool, *uc_tools], verbose=False)


class LangChainResponsesAgent(ResponsesAgent):
    """
    Wraps your LangChain AgentExecutor in an MLflow ResponsesAgent so it can be
    logged/served via MLflow 3.4+ Models-from-Code.
    """

    def __init__(self):
        # Build and cache the LangChain agent once per model load
        self.agent = build_agent()

    def _last_user_text(self, messages: List[Dict[str, Any]]) -> str:
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if user_msgs:
            return str(user_msgs[-1].get("content", ""))
        return str(messages[-1].get("content", "")) if messages else ""

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        # Convert Responses messages -> LangChain payload
        msgs = [m.model_dump() for m in request.input]
        input_text = self._last_user_text(msgs)

        # If you want to thread history, transform msgs -> your prompt's "chat_history"
        chat_history: List[Any] = []  # keep simple; extend if you want multi-turn memory

        result = self.agent.invoke({"input": input_text, "chat_history": chat_history})
        text = result["output"] if isinstance(result, dict) and "output" in result else str(result)

        # Return a single text output item (keeps UI clean, no "plan"/tool narration)
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text, str(uuid4()))],
            custom_outputs=request.custom_inputs,
        )

    # Optional: stream a single final item (compatible with Responses interface)
    def predict_stream(self, request: ResponsesAgentRequest):
        resp = self.predict(request)
        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=resp.output[0],
        )


# Register model object for MLflow Models-from-Code
# Build a single instance for local/testing use…
AGENT = LangChainResponsesAgent()
mlflow.models.set_model(AGENT)
