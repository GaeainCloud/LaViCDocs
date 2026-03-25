from __future__ import annotations

from pathlib import Path
from typing import List


class Retriever:
    """
    Lightweight retriever over local markdown/docs names.
    """

    def query(self, text: str):
        base = Path(__file__).resolve().parents[3] / "knowledge_base"
        if not base.exists():
            return []
        query = text.lower().strip()
        hits: List[str] = []
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            name = path.name.lower()
            if query and query in name:
                hits.append(str(path))
            if len(hits) >= 20:
                break
        return hits

class Librarian:
    """
    Manages schemas and rules.
    """

    def list_schema_files(self) -> List[str]:
        schema_dir = Path(__file__).resolve().parents[3] / "src" / "schemas"
        if not schema_dir.exists():
            return []
        return [str(path) for path in sorted(schema_dir.rglob("*.json"))]
