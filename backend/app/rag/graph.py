import asyncio
import json
import logging

from langgraph.graph import END, START, StateGraph
from starlette.concurrency import run_in_threadpool

from app.database.documents import require_patient
from app.exceptions import AppError
from app.observability import stage, telemetry_scope
from app.rag.nodes.analysis import analysis_node
from app.rag.nodes.fallback import fallback_node
from app.rag.nodes.final import final_node
from app.rag.nodes.generation import generation_node
from app.rag.nodes.relevance import relevance_node
from app.rag.nodes.retrieval import retrieval_node
from app.rag.nodes.rewrite import rewrite_node
from app.rag.nodes.timed import timed_node
from app.rag.nodes.validation import validation_node
from app.rag.routing import route_after_relevance, route_after_validation
from app.rag.runtime import RAGServices
from app.rag.state import AuthContext, RAGState
from app.schemas.rag import GenerationResult
from app.services.rag import response_from_result


def build_graph(services: RAGServices):
    builder = StateGraph(RAGState, context_schema=AuthContext)
    builder.add_node("query_analysis", timed_node("query_analysis", analysis_node(services)))
    builder.add_node("retrieval", timed_node("retrieval", retrieval_node(services), uses_runtime=True))
    builder.add_node("generation", timed_node("generation", generation_node(services)))
    builder.add_node("relevance", timed_node("relevance", relevance_node(services)))
    builder.add_node("insufficient_context", fallback_node)
    builder.add_node("rewrite", timed_node("rewrite", rewrite_node(services)))
    builder.add_node("validation", timed_node("validation", validation_node(services)))
    builder.add_node("final_response", final_node)
    builder.add_edge(START, "query_analysis")
    builder.add_edge("query_analysis", "retrieval")
    builder.add_edge("retrieval", "relevance")
    builder.add_conditional_edges(
        "relevance",
        lambda s: route_after_relevance(s, services.settings.max_query_retries),
        {"generation": "generation", "rewrite": "rewrite", "insufficient_context": "insufficient_context"},
    )
    builder.add_edge("rewrite", "retrieval")
    builder.add_edge("insufficient_context", END)
    builder.add_edge("generation", "validation")
    builder.add_conditional_edges(
        "validation",
        lambda s: route_after_validation(s, services.settings.max_generation_retries),
        {
            "final_response": "final_response",
            "generation": "generation",
            "insufficient_context": "insufficient_context",
        },
    )
    builder.add_edge("final_response", END)
    return builder.compile()


class GraphRAGService:
    def __init__(self, retrieval, llm, privacy, settings):
        self.services = RAGServices(retrieval, llm, privacy, settings)
        self.graph = build_graph(self.services)

    async def run(self, patient_id: str, question: str, document_type, request_id: str) -> RAGState:
        with telemetry_scope(request_id):
            return await self._run(patient_id, question, document_type, request_id)

    async def _run(self, patient_id: str, question: str, document_type, request_id: str) -> RAGState:
        require_patient(patient_id)
        with telemetry_scope(request_id), stage("privacy"):
            sanitized = await run_in_threadpool(self.services.privacy.sanitize, question)
        state: RAGState = {
            "patient_id": patient_id,
            "request_id": request_id,
            "original_query": sanitized,
            "current_query": sanitized,
            "document_type": document_type,
            "query_category": None,
            "retrieved_chunks": [],
            "relevant_chunks": [],
            "relevance_passed": False,
            "retry_count": 0,
            "generation_count": 0,
            "generated_answer": None,
            "context": [],
            "validation_passed": False,
            "validation_issues": [],
            "final_answer": None,
            "status": "processing",
        }
        from langsmith import tracing_context

        with telemetry_scope(request_id) as metrics, tracing_context(enabled=False):
            result = None
            try:
                with stage("rag_total"):
                    task = asyncio.create_task(
                        self.graph.ainvoke(
                            state,
                            context=AuthContext(patient_id, request_id),
                            config={"recursion_limit": 100},
                        )
                    )
                    try:
                        done, _ = await asyncio.wait(
                            {task}, timeout=self.services.settings.rag_timeout_seconds
                        )
                        if not done:
                            raise TimeoutError()
                        result = task.result()
                    finally:
                        if not task.done():
                            task.cancel()
                            await asyncio.gather(task, return_exceptions=True)
            except TimeoutError as exc:
                raise AppError("RAG_TIMEOUT", "Record query timed out.", 503) from exc
            finally:
                logging.getLogger("medical_rag.stages").info(
                    json.dumps(
                        {
                            "event": "rag_stages",
                            "request_id": request_id,
                            "status": result["status"] if result else "error",
                            "retry_count": result["retry_count"] if result else 0,
                            "generation_count": result["generation_count"] if result else 0,
                            **{k: round(v, 3) for k, v in metrics.timings.items()},
                            **metrics.counts,
                        }
                    )
                )
            return result

    async def query(self, patient_id: str, question: str, document_type, request_id: str):
        state = await self.run(patient_id, question, document_type, request_id)
        return response_from_result(
            GenerationResult.model_validate(state["generated_answer"]), state["context"], request_id
        )
