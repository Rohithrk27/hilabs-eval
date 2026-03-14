"""Optional Gemini-based validation when rules are uncertain."""

from __future__ import annotations

import os
from typing import Dict, Optional


def _load_gemini():
    try:
        import google.generativeai as genai  # type: ignore
    except Exception:
        return None
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
    except Exception:
        return None
    return model


def validate_with_gemini(entity: Dict) -> Optional[Dict[str, bool]]:
    """Return field-level booleans or None if not available."""
    model = _load_gemini()
    if not model:
        return None

    prompt = (
        "You are validating structured clinical entities extracted from OCR charts.\n"
        "Return JSON with boolean flags: entity_type_correct, assertion_correct, "
        "temporality_correct, subject_correct. Respond with JSON only.\n\n"
        f"Entity JSON: {entity}"
    )
    try:
        response = model.generate_content(prompt)
        text = response.text or "{}"
        # Very small, safe eval by using literal_eval to avoid code execution
        import ast

        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return {
                "entity_type_correct": bool(parsed.get("entity_type_correct", False)),
                "assertion_correct": bool(parsed.get("assertion_correct", False)),
                "temporality_correct": bool(parsed.get("temporality_correct", False)),
                "subject_correct": bool(parsed.get("subject_correct", False)),
            }
    except Exception:
        return None
    return None

