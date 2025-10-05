from typing import Dict, Any, List
import json
from pathlib import Path


class FileAuditExporter:
    """Simple file-based audit exporter for dev and tests.

    Appends JSON lines to a configured file path. In production this would be a durable sink.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def export(self, events: List[Dict[str, Any]]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e, default=str) + "\n")


__all__ = ["FileAuditExporter"]
