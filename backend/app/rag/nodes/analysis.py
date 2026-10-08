import re

from app.schemas.rag import AnalysisResult

SUMMARY_REQUEST = re.compile(
    r"\b(?:summari[sz]e|summari[sz]ation|summary|overview|recap)\b|"
    r"\b(?:medical|clinical|health)\s+history\b",
    re.IGNORECASE,
)


def analysis_node(services):
    async def analyze(state):
        # Route explicit summary requests locally: an LLM category prediction must
        # not send an all-records request through top-K semantic retrieval.
        if SUMMARY_REQUEST.search(state["original_query"]):
            return {"query_category": "clinical_summary", "document_type": state["document_type"]}
        result = await services.call(AnalysisResult, services.llm.analyze, state["current_query"])
        return {
            "query_category": result.query_category,
            "document_type": state["document_type"]
            or (result.document_type if result.confidence >= 0.9 else None),
        }

    return analyze
