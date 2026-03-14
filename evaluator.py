"""Core evaluation logic for clinical entity reliability.

This module orchestrates rule-based checks (and optionally LLM checks)
to score each entity on multiple dimensions, then aggregates metrics
across a file.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Iterable, List, Optional, Tuple

from metrics import MetricsAggregator
from rules import (
    attribute_completeness,
    detect_event_date,
    infer_assertion,
    infer_entity_type,
    infer_subject,
    infer_temporality,
)
from llm_validator import validate_with_gemini


# Allowed label vocabularies (fixed for reporting keys)
ENTITY_TYPES = [
    "MEDICINE",
    "PROBLEM",
    "PROCEDURE",
    "TEST",
    "VITAL_NAME",
    "IMMUNIZATION",
    "MEDICAL_DEVICE",
    "MENTAL_STATUS",
    "SDOH",
    "SOCIAL_HISTORY",
]

ASSERTIONS = ["POSITIVE", "NEGATIVE", "UNCERTAIN"]
TEMPORALITIES = ["CURRENT", "CLINICAL_HISTORY", "UPCOMING", "UNCERTAIN"]
SUBJECTS = ["PATIENT", "FAMILY_MEMBER"]


class Evaluator:
    """Evaluate a list of entity dictionaries and build a metrics report."""

    def __init__(self, use_llm: bool = False) -> None:
        self.use_llm = use_llm and bool(os.getenv("GEMINI_API_KEY"))
        self.metrics = MetricsAggregator(
            entity_types=ENTITY_TYPES,
            assertions=ASSERTIONS,
            temporalities=TEMPORALITIES,
            subjects=SUBJECTS,
        )

    def evaluate_entities(self, entities: Iterable[Dict]) -> Dict:
        for ent in entities:
            self._evaluate_single_entity(ent)
        return self.metrics.build_report()

    def _evaluate_single_entity(self, ent: Dict) -> None:
        """Run per-entity checks and update aggregate metrics."""

        text = (ent.get("text") or "").lower()
        heading = ent.get("heading") or ""

        # Rule-based expected labels
        expected_entity_type, type_confidence = infer_entity_type(ent, heading)
        expected_assertion, assertion_confidence = infer_assertion(text)
        expected_temporality, temporal_confidence = infer_temporality(text)
        expected_subject, subject_confidence = infer_subject(text)

        # LLM backstop when rules are uncertain and flag enabled
        llm_result = None
        if self.use_llm and self._needs_llm(
            [type_confidence, assertion_confidence, temporal_confidence, subject_confidence]
        ):
            llm_result = validate_with_gemini(ent)

        # Entity type correctness
        entity_type = ent.get("entity_type") or ""
        type_correct = self._is_label_correct(
            entity_type, expected_entity_type, type_confidence, llm_result, "entity_type"
        )

        # Assertion correctness
        assertion = ent.get("assertion") or ""
        assertion_correct = self._is_label_correct(
            assertion, expected_assertion, assertion_confidence, llm_result, "assertion"
        )

        # Temporality correctness
        temporality = ent.get("temporality") or ""
        temporality_correct = self._is_label_correct(
            temporality, expected_temporality, temporal_confidence, llm_result, "temporality"
        )

        # Subject correctness
        subject = ent.get("subject") or ""
        subject_correct = self._is_label_correct(
            subject, expected_subject, subject_confidence, llm_result, "subject"
        )

        # Event date accuracy (only when metadata includes date fields)
        date_has_metadata, date_present = detect_event_date(ent)

        # Attribute completeness (ratio or None)
        completeness = attribute_completeness(ent)

        # Update aggregate metrics
        self.metrics.add_entity(
            entity_type=entity_type,
            type_correct=type_correct,
            assertion=assertion,
            assertion_correct=assertion_correct,
            temporality=temporality,
            temporality_correct=temporality_correct,
            subject=subject,
            subject_correct=subject_correct,
            date_checked=date_has_metadata,
            date_correct=date_present,
            attribute_completeness=completeness,
        )

    @staticmethod
    def _needs_llm(confidences: List[float]) -> bool:
        # If all confidences are high enough (>0.6) we trust rules; otherwise allow LLM
        return any(c < 0.6 for c in confidences)

    @staticmethod
    def _is_label_correct(
        provided: str,
        expected: Optional[str],
        confidence: float,
        llm_result: Optional[Dict],
        field: str,
    ) -> bool:
        # If rule confident and expected available, compare
        if expected:
            if provided == expected:
                return True
            if confidence >= 0.6:
                return False
        # If LLM result present use it
        if llm_result and f"{field}_correct" in llm_result:
            return bool(llm_result[f"{field}_correct"])
        # Fallback: consider correct when uncertain (avoid false alarms)
        return provided != ""


def evaluate_file(input_path: str, use_llm: bool = False) -> Dict:
    """Convenience helper to evaluate one JSON file path."""
    with open(input_path, "r", encoding="utf-8") as f:
        entities = json.load(f)
    evaluator = Evaluator(use_llm=use_llm)
    return evaluator.evaluate_entities(entities)
