import re

from app.schemas.documents import DocumentType

TITLE_SIGNALS = {
    "discharge_summary": ("discharge summary", "discharge instructions", "discharge report"),
    "claim_document": ("insurance claim", "claim summary", "claim document", "claim form"),
    "prescription": ("medication prescription", "prescription", "prescription order"),
    "lab_report": ("laboratory", "lab report", "blood test report"),
    "diagnostic_report": (
        "ultrasound report",
        "radiology report",
        "imaging report",
        "retinal screening",
        "x-ray report",
        "mri report",
        "ct report",
        "echocardiogram report",
    ),
    "clinical_note": (
        "clinical note",
        "visit note",
        "consultation note",
        "consultation report",
        "nutrition consultation",
        "progress note",
        "follow-up note",
    ),
}


def classify_document(text: str, provided: DocumentType | None = None) -> DocumentType:
    if provided is not None:
        return provided
    lower = text.lower()
    # Prefer the document's own heading over incidental medications or lab values
    # in its body. Ignore an incidental heading far down a multi-section record.
    lines = [re.sub(r"\s+", " ", line).strip() for line in lower.splitlines() if line.strip()]
    for line in lines[:16]:
        if re.fullmatch(r"(?:rx|r\s*/\s*x|\u211e)[:.\s]*", line):
            return "prescription"
        if len(line) > 140:
            continue
        matches = [kind for kind, terms in TITLE_SIGNALS.items() if any(term in line for term in terms)]
        if len(matches) == 1:
            return matches[0]
    # A prescription without a formal heading often has dispense/refill/Sig
    # labels or multiple dose schedules. Do not treat one medication mention
    # in an ordinary note as enough evidence for a prescription.
    prescription_labels = len(re.findall(r"\b(?:sig|dispense|refills?|rx)\s*[:=]", lower))
    schedules = len(re.findall(
        r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b[^\n]{0,80}"
        r"\b(?:daily|nightly|bid|tid|qid|once|twice|every|bd|tds)\b", lower))
    if prescription_labels >= 2 or (prescription_labels >= 1 and schedules >= 1):
        return "prescription"
    signals = {
        "lab_report": ("hba1c", "laboratory", "reference range", "plasma glucose", "specimen", "lipid panel"),
        "prescription": ("prescribed", "prescription", "take daily", "orally", "refills", "dispense", "dosage", "sig:"),
        "claim_document": (
            "claim status",
            "claim number",
            "claim approved",
            "claim denied",
            "insurer paid",
            "patient responsibility",
        ),
        "discharge_summary": (
            "discharge diagnosis",
            "discharged home",
            "discharge instructions",
            "hospital course",
        ),
        "diagnostic_report": ("imaging findings", "ultrasound", "echogenicity", "retinopathy", "radiology"),
        "clinical_note": (
            "assessment and plan",
            "reason for visit",
            "interval history",
            "physical examination",
            "follow-up planned",
        ),
    }
    scores = {kind: sum(term in lower for term in terms) for kind, terms in signals.items()}
    best = max(scores.values())
    winners = [kind for kind, score in scores.items() if score == best]
    return winners[0] if best and len(winners) == 1 else "other"
