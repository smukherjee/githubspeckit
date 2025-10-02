import pytest
from adapters.observability.metrics import SimpleMetricsRegistry

# TEST-OBS-01A: Metrics key set compliance (FR-016, C-030)

def test_metrics_key_set_compliance():
    reg = SimpleMetricsRegistry()
    # simulate registration of required metrics (normally done at startup)
    for k in reg.REQUIRED_METRICS:
        reg.register(k)
    assert reg.has_required()
