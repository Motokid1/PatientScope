def route_after_relevance(state, max_retries: int) -> str:
    if state["relevance_passed"]:
        return "generation"
    if state["retry_count"] < max_retries:
        return "rewrite"
    return "insufficient_context"


def route_after_validation(state, max_retries: int) -> str:
    if state["validation_passed"]:
        return "final_response"
    if state["generation_count"] < max_retries + 1:
        return "generation"
    return "insufficient_context"
