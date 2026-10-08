from langgraph.runtime import Runtime

from app.exceptions import AppError
from app.rag.state import AuthContext, RAGState


def retrieval_node(services):
    async def retrieve(state: RAGState, runtime: Runtime[AuthContext]):
        if state["patient_id"] != runtime.context.patient_id:
            raise AppError("ISOLATION_VIOLATION", "Authenticated identity changed.", 503)
        if state["query_category"] == "clinical_summary":
            rows = await services.retrieval.retrieve_summary(
                runtime.context.patient_id, state["document_type"]
            )
        else:
            rows = await services.retrieval.retrieve(
                runtime.context.patient_id, state["current_query"], state["document_type"]
            )
        return {"retrieved_chunks": rows, "relevant_chunks": rows}

    return retrieve
