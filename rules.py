"""Rule-based validators for clinical entity reliability checks."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Tuple


# Basic vocabularies
NEGATION_TERMS = ["no", "denies", "without", "negative for"]
UNCERTAIN_TERMS = ["possible", "likely", "suspect", "suspected", "probable", "?", "rule out"]

HISTORY_TERMS = ["history", "past", "previous", "prior"]
UPCOMING_TERMS = ["scheduled", "planned", "plan", "next", "upcoming"]

FAMILY_TERMS = ["mother", "father", "brother", "sister", "family history", "aunt", "uncle", "cousin"]


ENTITY_TYPE_HINTS = {
    "MEDICINE": ["medication", "medications", "meds", "rx", "drug", "tablet", "capsule", "dose", "mg"],
    "PROBLEM": ["diagnosis", "problem", "condition", "disease", "hx"],
    "PROCEDURE": ["procedure", "surgery", "operated", "operation"],
    "TEST": ["lab", "test", "result", "panel", "cbc", "imaging", "scan"],
    "VITAL_NAME": ["blood pressure", "bp", "heart rate", "respiratory rate", "pulse", "temperature", "spo2", "vital"],
    "IMMUNIZATION": ["immunization", "immunisation", "vaccine", "vaccination"],
    "MEDICAL_DEVICE": ["device", "pacemaker", "stent", "implant", "catheter"],
    "MENTAL_STATUS": ["alert", "oriented", "mental", "cognition"],
    "SDOH": ["housing", "employment", "income", "food", "transport"],
    "SOCIAL_HISTORY": ["smoking", "alcohol", "social", "lives with", "occupation", "married", "divorced"],
}


ATTRIBUTE_EXPECTATIONS = {
    "MEDICINE": ["STRENGTH", "UNIT", "DOSE", "FREQUENCY", "ROUTE", "FORM"],
}


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def infer_assertion(text: str) -> Tuple[Optional[str], float]:
    """Infer assertion label from text; return (label, confidence)."""
    if _contains_any(text, NEGATION_TERMS):
        return "NEGATIVE", 0.9
    if _contains_any(text, UNCERTAIN_TERMS):
        return "UNCERTAIN", 0.75
    if text.strip():
        return "POSITIVE", 0.6
    return None, 0.0


def infer_temporality(text: str) -> Tuple[Optional[str], float]:
    if _contains_any(text, HISTORY_TERMS):
        return "CLINICAL_HISTORY", 0.85
    if _contains_any(text, UPCOMING_TERMS):
        return "UPCOMING", 0.85
    if text.strip():
        return "CURRENT", 0.5
    return None, 0.0


def infer_subject(text: str) -> Tuple[Optional[str], float]:
    if _contains_any(text, FAMILY_TERMS):
        return "FAMILY_MEMBER", 0.9
    if text.strip():
        return "PATIENT", 0.5
    return None, 0.0


def infer_entity_type(entity: Dict, heading: str) -> Tuple[Optional[str], float]:
    """Use heading and text heuristics to guess entity type."""
    text = (entity.get("text") or heading or "").lower()

    # Strong hint from heading
    for etype, hints in ENTITY_TYPE_HINTS.items():
        if any(h in heading.lower() for h in hints):
            return etype, 0.8

    # Weak hint from text keywords
    for etype, hints in ENTITY_TYPE_HINTS.items():
        if any(h in text for h in hints):
            return etype, 0.55

    return None, 0.0


def detect_event_date(entity: Dict) -> Tuple[bool, bool]:
    """Return (date_present_in_metadata, date_matches_text)."""
    metadata = entity.get("metadata_from_qa") or {}
    text = (entity.get("text") or "").lower()
    date_fields = []

    for field in ("exact_date", "derived_date"):
        value = metadata.get(field)
        if isinstance(value, list):
            date_fields.extend(value)
        elif value:
            date_fields.append(str(value))

    if not date_fields:
        return False, False

    for date_str in date_fields:
        if not date_str:
            continue
        if _date_in_text(date_str, text):
            return True, True
    return True, False


def _date_in_text(date_str: str, text: str) -> bool:
    """Simple normalization to match dates inside text."""
    normalized = re.sub(r"\D", "", date_str)
    normalized_text = re.sub(r"\D", "", text)
    if normalized and normalized in normalized_text:
        return True
    # fallback raw substring match
    return date_str.lower() in text


def attribute_completeness(entity: Dict) -> Optional[float]:
    """Return completeness ratio for known attribute sets (currently MEDICINE)."""
    etype = entity.get("entity_type")
    expected = ATTRIBUTE_EXPECTATIONS.get(etype)
    if not expected:
        return None

    metadata = entity.get("metadata_from_qa") or {}
    if not isinstance(metadata, dict):
        return 0.0

    present = 0
    for key in expected:
        value = metadata.get(key)
        if value not in (None, ""):
            present += 1
    return present / len(expected)
