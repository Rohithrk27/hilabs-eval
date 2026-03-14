# Clinical Entity Reliability Evaluation

This project evaluates the reliability of a clinical OCR→NLP pipeline by scoring extracted entities against rule-based checks (with optional Gemini backstop).

## Approach
- **Rule heuristics** in `rules.py` detect negation, temporality, family mentions, entity-type hints, event-date presence in text, and MEDICINE attribute completeness (strength/unit/dose/frequency/route/form).
- **Evaluator** in `evaluator.py` applies rules per entity, aggregates correctness with `metrics.py`, and produces schema-aligned error rates plus event-date accuracy and attribute completeness.
- **Optional LLM validation** in `llm_validator.py` calls Gemini when rule confidence is low (requires `GEMINI_API_KEY` and `google-generativeai`).
- **CLI driver** `test.py` supports single-file or directory inputs, writing per-chart reports to `output/` with the same filenames as inputs.
- **Report template** `report.md` provides slots for quantitative summary, error heatmap, systemic weaknesses, and guardrails.

## Repository layout
- `test.py` – entry script.
- `evaluator.py`, `rules.py`, `metrics.py`, `llm_validator.py` – evaluation logic.
- `output/` – generated per-chart evaluation JSONs (already populated for the provided dataset).
- `report.md` – template for narrative findings.
- `requirements.txt` – Gemini client dependency (only needed for `--use-llm`).
- `test_data/` – input charts (restored locally; typically excluded from pushes).

## Running
From the repo root:
- Directory mode: `python test.py test_data output`
- Single file: `python test.py test_data/019M72177_N991-796129_20241213/019M72177_N991-796129_20241213.json output/019M72177_N991-796129_20241213.json`
- Enable Gemini: set `GEMINI_API_KEY` then add `--use-llm` to either command.

## Outputs
Each output JSON matches the required schema, containing:
- `entity_type_error_rate`, `assertion_error_rate`, `temporality_error_rate`, `subject_error_rate`
- `event_date_accuracy`
- `attribute_completeness`
- `file_name`

## Notes
- If `google-generativeai` cannot be installed (e.g., network blocks), the framework runs with rules only.
- Input safety: missing fields and empty metadata are handled gracefully.
