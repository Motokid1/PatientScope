from app.schemas.rag import GenerationResult
from app.services.rag import response_from_result


async def final_node(state):
    result = response_from_result(
        GenerationResult.model_validate(state["generated_answer"]), state["context"], state["request_id"]
    )
    return {"final_answer": result.answer, "status": result.status}
