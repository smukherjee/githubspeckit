#!/usr/bin/env python
"""Generate FR → Task mapping section for tasks.md from explicit task lines.

Parsing rules:
 - Task lines start with '- ' followed by TASK-ID pattern (TEST-|IMPL-|DEFER-) and description.
 - FR references appear in parentheses like (FR-012, FR-030) or inline after description.
 - We rely on explicit mapping already encoded in tasks.md lane sections; this script recomputes mapping.

Output: prints a sorted mapping block you can replace in tasks.md.
"""
from __future__ import annotations
import re
from pathlib import Path
from collections import defaultdict
from script_logger import get_logger

logger = get_logger("gen_fr_task_mapping")

TASK_LINE_RE = re.compile(r"^-\s+(?P<id>(TEST|IMPL|DEFER)-[A-Z0-9-]+)\s+.*?(?P<frs>\(FR-[0-9,\s-]+\))?", re.IGNORECASE)
FR_RE = re.compile(r"FR-\d{3}")

def extract():
    tasks_path = Path(__file__).resolve().parent.parent / "specs/001-modern-enterprise-grade/tasks.md"
    lines = tasks_path.read_text().splitlines()
    fr_to_tasks: dict[str, set[str]] = defaultdict(set)
    for line in lines:
        m = TASK_LINE_RE.match(line.strip())
        if not m:
            continue
        task_id = m.group('id')
        fr_block = m.group('frs') or ""
        for fr in FR_RE.findall(fr_block):
            fr_to_tasks[fr].add(task_id)
    return fr_to_tasks

def main():
    fr_to_tasks = extract()
    mapping = []
    for fr in sorted(fr_to_tasks.keys()):
        tasks = ", ".join(sorted(fr_to_tasks[fr]))
        mapping.append(f"- {fr}: {tasks}")
    
    logger.json_output({
        "mapping_count": len(mapping),
        "fr_count": len(fr_to_tasks),
        "mapping": mapping
    })

if __name__ == "__main__":
    main()
