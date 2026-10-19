"""
RAG Chain with Grounded Runbook Citations.

Retrieves top-k runbook chunks from Chroma DB and prompts the LLM
to answer strictly from context with precise citations.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import SystemMessage, HumanMessage
from agent.llm import get_llm, clean_output
from rag.ingest import query_runbooks, DEFAULT_DB_PATH

SYSTEM_PROMPT = """You are an expert AI SRE / ChatOps diagnostic agent.
Your job is to diagnose microservice incidents and recommend remediations based STRICTLY on the provided runbook snippets.

STRICT RULES:
1. Use ONLY the provided context to answer the question.
2. If the context does not contain sufficient information to diagnose the issue or provide a fix, explicitly state:
   "Based on the available runbooks, there is insufficient information to diagnose this incident."
3. NEVER invent or hallucinate commands, environment variables, or causes not grounded in the context.
4. Structure your response clearly:
   - **Diagnosis**: What is happening and the root cause.
   - **How to Confirm**: Exact commands to run (Docker, logs, PromQL).
   - **Recommended Fix**: Step-by-step resolution steps.
   - **Sources**: List the runbooks and sections referenced.
"""

USER_TEMPLATE = """CONTEXT FROM RUNBOOKS:
---------------------
{context}
---------------------

INCIDENT / QUESTION:
{question}

Provide your grounded diagnosis, confirmation commands, and remediation steps following the rules above."""


class RAGChain:
    """
    Retrieval-Augmented Generation chain over SRE runbooks.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH, top_k: int = 3, model_id: Optional[str] = None):
        self.db_path = db_path
        self.top_k = top_k
        self.llm = get_llm(model_id=model_id)

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """Fetch top-k runbook snippets from vector store."""
        return query_runbooks(query, db_path=self.db_path, top_k=self.top_k)

    def format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into a prompt context string."""
        if not chunks:
            return "No matching runbook snippets found."

        formatted_parts = []
        for i, c in enumerate(chunks, start=1):
            formatted_parts.append(
                f"[Source {i}]: {c['title']} | Section: {c['section']} (File: {c['source']})\n"
                f"{c['snippet']}\n"
            )
        return "\n".join(formatted_parts)

    def run(self, question: str) -> Dict[str, Any]:
        """
        Executes RAG: retrieval -> prompt building -> LLM invocation -> output cleaning.
        Returns a dict containing the question, answer, and unique cited sources.
        """
        # 1. Retrieve
        chunks = self.retrieve(question)

        # 2. Extract unique sources
        unique_sources: List[Dict[str, Any]] = []
        seen_keys = set()
        for c in chunks:
            key = (c["source"], c["section"])
            if key not in seen_keys:
                seen_keys.add(key)
                unique_sources.append({
                    "title": c["title"],
                    "source": c["source"],
                    "section": c["section"],
                    "failure_type": c["failure_type"],
                    "service": c["service"],
                    "score": c["score"],
                })

        # 3. Assemble prompt
        context_str = self.format_context(chunks)
        user_message_text = USER_TEMPLATE.format(context=context_str, question=question)

        # 4. Invoke LLM
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_message_text),
        ]
        response = self.llm.invoke(messages)

        # 5. Clean output (drops reasoning / <think> tags)
        cleaned_answer = clean_output(response)

        return {
            "question": question,
            "answer": cleaned_answer,
            "sources": unique_sources,
            "retrieved_chunks": chunks,
        }
