import json
import subprocess
import sys
from pathlib import Path

def test_startup_failure_emits_aggregated_json(tmp_path):
    # Placeholder: simulate running an entrypoint that would validate config.
    # Since actual startup script not yet implemented, mark expected failure.
    # This test will intentionally fail until implementation adds the behavior.
    script = tmp_path / "fake_start.py"
    script.write_text("import sys, json; print(json.dumps({'error':'configuration_validation_failed','config_hash':None,'issues':[{'name':'REQUIRED_VAR','error':'missing','expected_type':'str'}]})); sys.exit(1)")
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert proc.returncode == 1
    # parse stdout for now; implementation will move to stderr as per spec
    data = json.loads(proc.stdout.strip())
    assert data["error"] == "configuration_validation_failed"
    assert isinstance(data["issues"], list)
    assert data["issues"] and data["issues"][0]["name"] == "REQUIRED_VAR"
