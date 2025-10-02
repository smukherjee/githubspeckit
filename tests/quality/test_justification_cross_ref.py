import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]

def test_justification_ids_match_registry():
    # collect JUSTIFY:<ID> markers
    code_ids = set()
    for path in ROOT.rglob("*.py"):
        if "venv" in path.as_posix() or ".venv" in path.as_posix():
            continue
        txt = path.read_text(errors="ignore")
        for m in re.findall(r"JUSTIFY:([A-Za-z0-9_-]+)", txt):
            code_ids.add(m)
    registry_file = ROOT / "quality_justifications.yaml"
    if not registry_file.exists():
        assert not code_ids, "Found justification markers but no registry file present"
        return
    data = yaml.safe_load(registry_file.read_text()) or {}
    registry_ids = set(data.keys())
    # every code id must appear in registry
    missing = code_ids - registry_ids
    assert not missing, f"Missing justification entries for IDs: {missing}"
    # optional: warn on stale registry entries (not failing for now)
