"""Log export orchestrator (IMPL-OBS-06) with bounds enforcement (TEST-OBS-05).

Phase 2 in-memory implementation operating on the in-memory structured log sink.
Provides a size-limited export of most recent log records with truncation metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class LogExportResult:
    records: List[Dict[str, Any]]
    truncated: bool
    total_available: int


class LogExportService:
    def __init__(self, *, sink: Any, max_limit: int = 500) -> None:
        self.sink = sink
        self.max_limit = max_limit

    def export_latest(self, limit: int) -> LogExportResult:
        if limit <= 0:
            return LogExportResult(records=[], truncated=False, total_available=len(self.sink.records))
        effective = min(limit, self.max_limit)
        total = len(self.sink.records)
        # take from end (most recent)
        selected = self.sink.records[-effective:][::-1]  # newest first
        truncated = total > effective
        return LogExportResult(records=selected, truncated=truncated, total_available=total)


__all__ = ["LogExportService", "LogExportResult"]
