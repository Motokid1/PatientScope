from app.schemas.rag import RelevanceResult
from app.services.rag import format_context


def relevance_node(services):
    async def relevance(state):
        rows = (
            state["retrieved_chunks"]
            if state["query_category"] == "clinical_summary"
            else [r for r in state["retrieved_chunks"] if r["score"] >= services.settings.relevance_threshold]
        )
        passed = bool(rows)
        # Completed, owned records are evidence for their own summary. A broad
        # request has no specific fact for the question-answer grader to match.
        if (
            passed
            and state["query_category"] != "clinical_summary"
            and services.settings.llm_relevance_enabled
        ):
            result = await services.call(
                RelevanceResult,
                services.llm.grade,
                state["original_query"],
                format_context(rows, services.settings.max_context_chars),
            )
            passed = result.relevant and result.confidence >= services.settings.relevance_threshold
        return {"relevant_chunks": rows if passed else [], "relevance_passed": passed}

    return relevance
