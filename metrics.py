"""Aggregation utilities for computing error rates and summary metrics."""

from __future__ import annotations

from typing import Dict, List, Optional


def _safe_rate(correct: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min(1.0, 1 - (correct / total)))


class MetricsAggregator:
    """Track running counts and build the final report structure."""

    def __init__(
        self,
        entity_types: List[str],
        assertions: List[str],
        temporalities: List[str],
        subjects: List[str],
    ) -> None:
        self.entity_types = entity_types
        self.assertions = assertions
        self.temporalities = temporalities
        self.subjects = subjects

        self.entity_totals = {k: 0 for k in entity_types}
        self.entity_correct = {k: 0 for k in entity_types}

        self.assertion_totals = {k: 0 for k in assertions}
        self.assertion_correct = {k: 0 for k in assertions}

        self.temporality_totals = {k: 0 for k in temporalities}
        self.temporality_correct = {k: 0 for k in temporalities}

        self.subject_totals = {k: 0 for k in subjects}
        self.subject_correct = {k: 0 for k in subjects}

        self.date_total = 0
        self.date_correct = 0

        self.completeness_scores: List[float] = []

    def add_entity(
        self,
        *,
        entity_type: str,
        type_correct: bool,
        assertion: str,
        assertion_correct: bool,
        temporality: str,
        temporality_correct: bool,
        subject: str,
        subject_correct: bool,
        date_checked: bool,
        date_correct: bool,
        attribute_completeness: Optional[float],
    ) -> None:
        if entity_type in self.entity_totals:
            self.entity_totals[entity_type] += 1
            if type_correct:
                self.entity_correct[entity_type] += 1

        if assertion in self.assertion_totals:
            self.assertion_totals[assertion] += 1
            if assertion_correct:
                self.assertion_correct[assertion] += 1

        if temporality in self.temporality_totals:
            self.temporality_totals[temporality] += 1
            if temporality_correct:
                self.temporality_correct[temporality] += 1

        if subject in self.subject_totals:
            self.subject_totals[subject] += 1
            if subject_correct:
                self.subject_correct[subject] += 1

        if date_checked:
            self.date_total += 1
            if date_correct:
                self.date_correct += 1

        if attribute_completeness is not None:
            self.completeness_scores.append(attribute_completeness)

    def build_report(self) -> Dict:
        entity_type_error = {
            k: _safe_rate(self.entity_correct[k], self.entity_totals[k]) for k in self.entity_types
        }
        assertion_error = {
            k: _safe_rate(self.assertion_correct[k], self.assertion_totals[k]) for k in self.assertions
        }
        temporality_error = {
            k: _safe_rate(self.temporality_correct[k], self.temporality_totals[k])
            for k in self.temporalities
        }
        subject_error = {
            k: _safe_rate(self.subject_correct[k], self.subject_totals[k]) for k in self.subjects
        }

        if self.date_total == 0:
            event_date_accuracy = 0.0
        else:
            event_date_accuracy = self.date_correct / self.date_total

        if not self.completeness_scores:
            attribute_completeness = 0.0
        else:
            attribute_completeness = sum(self.completeness_scores) / len(self.completeness_scores)

        return {
            "entity_type_error_rate": entity_type_error,
            "assertion_error_rate": assertion_error,
            "temporality_error_rate": temporality_error,
            "subject_error_rate": subject_error,
            "event_date_accuracy": event_date_accuracy,
            "attribute_completeness": attribute_completeness,
        }

