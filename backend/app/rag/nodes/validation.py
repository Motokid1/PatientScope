from app.schemas.rag import GenerationResult
from app.services.validation import OutputValidationService


def validation_node(services):
    validator = OutputValidationService(services)

    async def validate(state):
        result = await validator.validate(
            state["original_query"],
            GenerationResult.model_validate(state["generated_answer"]),
            state["context"],
        )
        return {"validation_passed": result.passed, "validation_issues": result.issues}

    return validate
