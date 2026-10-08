import re

from starlette.concurrency import run_in_threadpool

from app.schemas.rag import IntentResult, RewriteResult


def rewrite_node(services):
    async def rewrite(state):
        result = await services.call(RewriteResult, services.llm.rewrite, state["original_query"])
        original_numbers = set(re.findall(r"\d+(?:\.\d+)?", state["original_query"]))
        rewritten_numbers = set(re.findall(r"\d+(?:\.\d+)?", result.rewritten_query))
        accepted = result.preserves_intent and rewritten_numbers <= original_numbers
        if accepted:
            intent = await services.call(
                IntentResult, services.llm.check_intent, state["original_query"], result.rewritten_query
            )
            accepted = intent.passed
        query = state["current_query"]
        if accepted:
            query = await run_in_threadpool(services.privacy.sanitize, result.rewritten_query)
        return {"current_query": query, "retry_count": state["retry_count"] + 1}

    return rewrite
