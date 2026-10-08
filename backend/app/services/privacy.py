import json
import re
from pathlib import Path
from typing import Protocol

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import SpacyNlpEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from app.exceptions import AppError
from app.services.clinical_terms import DEFAULT_CLINICAL_TERMS


class PrivacyService(Protocol):
    def sanitize(self, text: str) -> str: ...
    def has_identifiers(self, text: str) -> bool: ...


class PresidioPrivacy:
    """Mask direct identifiers; preserve dates and clinical facts for longitudinal QA.

    Dates and clinical facts still constitute sensitive health data. Sanitized
    records must retain the same access controls as original medical records.
    """

    ENTITIES = [
        "PERSON",
        "PHONE_NUMBER",
        "EMAIL_ADDRESS",
        "LOCATION",
        "US_SSN",
        "MEDICAL_LICENSE",
        "MEDICAL_RECORD_ID",
        "US_PASSPORT",
        "CREDIT_CARD",
    ]

    def __init__(
        self,
        model: str = "en_core_web_sm",
        threshold: float = 0.4,
        clinical_terms: list[str] | None = None,
        clinical_terms_file: str | None = None,
    ):
        import spacy

        if not spacy.util.is_package(model):
            raise AppError("PRIVACY_CONFIGURATION", "Privacy model is not installed.", 503)
        self.threshold = threshold
        terms = list(DEFAULT_CLINICAL_TERMS) + list(clinical_terms or [])
        if clinical_terms_file:
            try:
                path = Path(clinical_terms_file)
                content = path.read_text(encoding="utf-8")
                extra = (
                    json.loads(content)
                    if path.suffix.lower() == ".json"
                    else [
                        line.strip()
                        for line in content.splitlines()
                        if line.strip() and not line.lstrip().startswith("#")
                    ]
                )
                if not isinstance(extra, list) or any(
                    not isinstance(term, str) or not term.strip() for term in extra
                ):
                    raise ValueError("Invalid clinical glossary")
                terms.extend(extra)
            except Exception as exc:
                raise AppError(
                    "PRIVACY_CONFIGURATION", "Clinical terminology file is invalid or unavailable.", 503
                ) from exc
        self.clinical_terms = {" ".join(term.casefold().split()) for term in terms}
        engine = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": model}])
        engine.load()
        self.analyzer = AnalyzerEngine(nlp_engine=engine, supported_languages=["en"])
        # Presidio's default email recognizer validates via a downloadable public
        # suffix list. Use local pattern recognition, including internal domains,
        # so privacy processing needs no network or writable on-disk cache.
        self.analyzer.registry.remove_recognizer("EmailRecognizer")
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="EMAIL_ADDRESS",
                name="OfflineEmailRecognizer",
                patterns=[Pattern("email", r"(?i)\b[\w.+-]+@[\w.-]+\b", 0.9)],
            )
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="MEDICAL_RECORD_ID",
                patterns=[
                    Pattern(
                        "record_identifier",
                        r"(?i)\b(?:MRN|patient\s*id|record\s*(?:id|number)|insurance\s*id)\s*[:#-]?\s*[A-Z0-9-]{3,}",
                        0.95,
                    )
                ],
            )
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="PHONE_NUMBER",
                patterns=[
                    Pattern("labelled_phone", r"(?i)\b(?:phone|mobile|tel)\s*[:#-]?\s*\+?[\d ()-]{8,20}", 0.9)
                ],
            )
        )
        self.anonymizer = AnonymizerEngine()

    def findings(self, text: str):
        try:
            # Ignore existing placeholders; NER can classify placeholder entity names.
            clean = re.sub(r"<[A-Z_]+>", lambda m: " " * len(m.group()), text)
            findings = self.analyzer.analyze(
                text=clean, language="en", entities=self.ENTITIES, score_threshold=self.threshold
            )
            # Correct exact clinical spans only for PERSON NER, never labelled names.
            # Other recognizers (IDs, email, phone) always retain precedence.
            return [
                r
                for r in findings
                if not (
                    r.entity_type == "PERSON"
                    and " ".join(text[r.start : r.end].casefold().split()) in self.clinical_terms
                    and not re.search(
                        r"(?i)\b(?:patient(?:\s+name)?|name|doctor|physician|dr\.?)\s*[:=-]?\s*$",
                        text[max(0, r.start - 60) : r.start],
                    )
                )
            ]
        except Exception as exc:
            raise AppError("PRIVACY_UNAVAILABLE", "Privacy processing is unavailable.", 503) from exc

    def sanitize(self, text: str) -> str:
        try:
            return self.anonymizer.anonymize(
                text=text,
                analyzer_results=self.findings(text),
                operators={
                    entity: OperatorConfig("replace", {"new_value": f"<{entity}>"})
                    for entity in self.ENTITIES
                },
            ).text
        except AppError:
            raise
        except Exception as exc:
            raise AppError("PRIVACY_UNAVAILABLE", "Privacy processing is unavailable.", 503) from exc

    def has_identifiers(self, text: str) -> bool:
        return bool(self.findings(text))
