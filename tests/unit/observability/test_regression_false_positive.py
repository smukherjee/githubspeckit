import pytest

# TEST-OBS-09A: Performance regression false positive filtering (hash differentiation) (FR-074)

def test_regression_detector_filters_transient_spikes():
    from observability.regression_detector import RegressionDetector
    rd = RegressionDetector(window_size=3, threshold_ms=200)
    # initial low values
    assert not rd.observe(100)
    assert not rd.observe(110)
    # single spike should not trigger (transient)
    assert not rd.observe(500)
    # sustained high values should trigger
    rd = RegressionDetector(window_size=3, threshold_ms=200)
    assert not rd.observe(250)
    assert not rd.observe(260)
    assert rd.observe(270)
