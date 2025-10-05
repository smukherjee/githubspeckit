"""Log export orchestrator (IMPL-OBS-06) with bounds enforcement (TEST-OBS-05).

Phase 2 in-memory implementation operating on the in-memory structured log sink.
Provides a size-limited export of most recent log records with truncation metadata.
Implements FR-016 and FR-072: filtered log export with time bounds, category filtering,
tenant isolation, and field redaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from adapters.logging.redaction import redact_dict, REDACT_KEYS


@dataclass
class LogExportResult:
    records: List[Dict[str, Any]]
    truncated: bool
    total_available: int
    reason: Optional[str] = None


class LogExportService:
    """Log export service with filtering and redaction (FR-016, FR-072, FR-073).
    
    Supports:
    - Time window filtering (since/until timestamps)
    - Tenant isolation (tenant_id filter)
    - Category filtering
    - Correlation ID filtering
    - Field redaction for sensitive data
    - Size bounds (max 10k events per C-006)
    - Truncation metadata when limits exceeded
    """
    
    def __init__(self, *, sink: Any, max_limit: int = 10000) -> None:
        self.sink = sink
        self.max_limit = max_limit  # FR-072: max events per export

    def export_latest(
        self,
        limit: int = 100,
        tenant_id: Optional[str] = None,
        category: Optional[str] = None,
        correlation_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> LogExportResult:
        """Export logs with filtering and redaction.
        
        Args:
            limit: Maximum records to return (capped at max_limit)
            tenant_id: Filter by tenant ID
            category: Filter by log category/level
            correlation_id: Filter by correlation ID
            since: Lower bound timestamp (inclusive)
            until: Upper bound timestamp (exclusive)
            
        Returns:
            LogExportResult with filtered, redacted records and truncation metadata
        """
        if limit <= 0:
            return LogExportResult(
                records=[],
                truncated=False,
                total_available=len(self.sink.records)
            )
        
        # Apply filters
        filtered = self._apply_filters(
            self.sink.records,
            tenant_id=tenant_id,
            category=category,
            correlation_id=correlation_id,
            since=since,
            until=until,
        )
        
        # Apply limit (capped at max_limit per FR-072)
        effective = min(limit, self.max_limit)
        total_filtered = len(filtered)
        
        # Take most recent records within limit
        selected = filtered[-effective:] if effective < total_filtered else filtered
        selected = selected[::-1]  # Newest first
        
        # Apply redaction to all records (FR-073)
        redacted_records = []
        for record in selected:
            redacted, _ = redact_dict(record)
            redacted_records.append(redacted)
        
        # Determine truncation
        truncated = total_filtered > effective
        reason = None
        if truncated:
            reason = "size_limit"  # Per C-006: explicit boundary indicator
        
        return LogExportResult(
            records=redacted_records,
            truncated=truncated,
            total_available=total_filtered,
            reason=reason,
        )
    
    def _apply_filters(
        self,
        records: List[Dict[str, Any]],
        tenant_id: Optional[str],
        category: Optional[str],
        correlation_id: Optional[str],
        since: Optional[datetime],
        until: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """Apply all filters to records."""
        filtered = records
        
        # Tenant filter
        if tenant_id:
            filtered = [r for r in filtered if r.get("tenant_id") == tenant_id]
        
        # Category filter (level field)
        if category:
            filtered = [r for r in filtered if r.get("level") == category]
        
        # Correlation ID filter
        if correlation_id:
            filtered = [r for r in filtered if r.get("correlation_id") == correlation_id]
        
        # Time bounds filters
        if since or until:
            filtered = self._filter_by_time(filtered, since, until)
        
        return filtered
    
    def _filter_by_time(
        self,
        records: List[Dict[str, Any]],
        since: Optional[datetime],
        until: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """Filter records by timestamp bounds."""
        result = []
        for record in records:
            ts_str = record.get("ts")
            if not ts_str:
                continue
            
            try:
                # Parse ISO8601 timestamp
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                
                # Apply bounds
                if since and ts < since:
                    continue
                if until and ts >= until:
                    continue
                
                result.append(record)
            except (ValueError, AttributeError):
                # Skip records with invalid timestamps
                continue
        
        return result


__all__ = ["LogExportService", "LogExportResult"]
