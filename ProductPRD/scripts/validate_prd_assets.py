#!/usr/bin/env python3
"""Validate PRD markdown/html assets against team standards."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

MD_REQUIRED_PATTERNS = [
    r"(?im)^##\s*0\.",
    r"(?im)^##\s*1\.",
    r"(?im)^##\s*2\.",
    r"(?im)^##\s*3\.",
    r"(?im)^##\s*4\.",
    r"(?im)^##\s*5\.",
    r"REQ-\d{3}",
]

HTML_REQUIRED_PATTERNS = [
    r"mermaid",
    r"flowchart",
    r"sequenceDiagram",
    r"stateDiagram",
]


def check_patterns(path: Path, patterns: list[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for pat in patterns:
        if not re.search(pat, text):
            errors.append(f"Missing required pattern `{pat}` in {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PRD markdown + html")
    parser.add_argument("--md", required=True, help="Path to PRD markdown file")
    parser.add_argument("--html", required=True, help="Path to PRD html file")
    args = parser.parse_args()

    md_path = Path(args.md)
    html_path = Path(args.html)

    errors: list[str] = []

    if not md_path.exists():
        errors.append(f"Markdown file not found: {md_path}")
    else:
        errors.extend(check_patterns(md_path, MD_REQUIRED_PATTERNS))

    if not html_path.exists():
        errors.append(f"HTML file not found: {html_path}")
    else:
        errors.extend(check_patterns(html_path, HTML_REQUIRED_PATTERNS))

    if errors:
        print("PRD validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PRD validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
