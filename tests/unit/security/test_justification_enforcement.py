"""TEST-SEC-13: Justification enforcement gate.

Ensures every required justification entry exists and is not past review date.
Will fail until gate implementation (IMPL-SEC-14) provided.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yaml

from quality.justification_gate import validate_justifications_fresh


def test_justification_enforcement_gate(tmp_path: Path):
    reg = tmp_path / "quality_justifications.yaml"
    reg.write_text(
        yaml.safe_dump(
            {
                "entries": [
                    {
                        "id": "JUS-001",
                        "area": "complexity",
                        "description": "Test justification",
                        "rationale": "demo",
                        "review_by": (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat(),
                        "owner": "team",
                    }
                ]
            }
        )
    )
    try:
        ok = validate_justifications_fresh(reg)
    except NotImplementedError:
        assert False, "Justification gate not implemented"
    else:
        assert ok is True
