from app.rag.prompts import FALLBACK


async def fallback_node(state):
    return {
        "generated_answer": {"answer": FALLBACK, "source_ids": []},
        "context": [],
        "final_answer": FALLBACK,
        "status": "insufficient_context",
    }
