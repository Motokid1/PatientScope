from app.rag.prompts import FALLBACK
from app.schemas.rag import GenerationResult
from app.services.rag import format_context


def generation_node(services):
    async def generate(state):
        context = format_context(state["relevant_chunks"], services.settings.max_context_chars)
        if not context:
            result = GenerationResult(answer=FALLBACK, source_ids=[])
        else:
            result = await services.call(
                GenerationResult,
                services.llm.generate,
                state["original_query"],
                context,
                strict=state["generation_count"] > 0,
            )
        return {
            "generated_answer": result.model_dump(),
            "context": context,
            "generation_count": state["generation_count"] + 1,
        }

    return generate
