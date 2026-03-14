"""Entry point for evaluating clinical entity extraction reliability.

Usage:
    python test.py input.json output.json
    python test.py test_data/ output/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from evaluator import evaluate_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clinical entity evaluation")
    parser.add_argument("input", help="Input JSON file or directory containing JSON files")
    parser.add_argument("output", help="Output JSON file or directory")
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Enable optional Gemini validation when rules are uncertain",
    )
    return parser.parse_args()


def iter_input_files(input_path: Path) -> Iterable[Path]:
    if input_path.is_file():
        yield input_path
    else:
        for path in input_path.rglob("*.json"):
            yield path


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if input_path.is_file():
        report = evaluate_file(str(input_path), use_llm=args.use_llm)
        report["file_name"] = input_path.name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return

    # Directory mode
    output_path.mkdir(parents=True, exist_ok=True)
    for file_path in iter_input_files(input_path):
        report = evaluate_file(str(file_path), use_llm=args.use_llm)
        report["file_name"] = file_path.name
        out_file = output_path / file_path.name
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()

