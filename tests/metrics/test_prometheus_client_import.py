import importlib


def test_prometheus_client_import_and_counter():
    mod = importlib.import_module("prometheus_client")
    counter = mod.Counter("test_prom_client_counter_total", "Test counter")
    counter.inc()
    # Export metrics text to ensure registry interaction works
    exposition = mod.generate_latest()
    assert b"test_prom_client_counter_total" in exposition
