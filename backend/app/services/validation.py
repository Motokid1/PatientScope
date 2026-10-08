import re

from starlette.concurrency import run_in_threadpool

from app.rag.prompts import FALLBACK
from app.schemas.rag import ValidationResult

INJECTION_ARTIFACTS = re.compile(
    r"ignore (?:all )?(?:previous |system )?instructions|reveal all patients|"
    r"system (?:prompt|instructions)|show (?:all|every) patient|"
    r"(?:api[ _-]?key|jwt[ _-]?secret)\s*[:=]",
    re.IGNORECASE,
)


class OutputValidationService:
    def __init__(self, services):
        self.services = services

    async def validate(self, question, result, context) -> ValidationResult:
        if result.answer == FALLBACK:
            return ValidationResult(
                passed=not result.source_ids, issues=[] if not result.source_ids else ["fallback_sources"]
            )
        ids = set(result.source_ids)
        available = {r["document_id"] for r in context}
        if not ids or not ids <= available:
            return ValidationResult(passed=False, issues=["invalid_citations"])
        cited = [r for r in context if r["document_id"] in ids]
        issues = []
        if INJECTION_ARTIFACTS.search(result.answer):
            issues.append("prompt_injection_artifact")
        if await run_in_threadpool(self.services.privacy.has_identifiers, result.answer):
            issues.append("identifying_information")
        answer_numbers = set(re.findall(r"\d+(?:\.\d+)?", result.answer))
        evidence_numbers = set(
            re.findall(
                r"\d+(?:\.\d+)?", " ".join(r["text"] + " " + (r["document_date"] or "") for r in cited)
            )
        )
        if not answer_numbers <= evidence_numbers:
            issues.append("unsupported_numeric_claim")
        if issues:
            return ValidationResult(passed=False, issues=issues)
        validated = await self.services.call(
            ValidationResult, self.services.llm.validate, question, result.answer, cited
        )
        if validated.passed and validated.issues:
            return ValidationResult(passed=False, issues=["inconsistent_validation"])
        return validated
