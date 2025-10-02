from adapters.observability.metrics import SimpleMetricsRegistry

def test_required_metrics_registered():
    reg = SimpleMetricsRegistry()
    # simulate startup registration of required metrics
    for m in reg.REQUIRED_METRICS:
        reg.register(m)
    missing = reg.REQUIRED_METRICS - reg.keys()
    assert not missing, f"Missing required metrics: {missing}"
