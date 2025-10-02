from auth_core.registry import default_registry

def test_only_password_provider_present_phase2():
    reg = default_registry()
    assert reg.list_provider_names() == ["password"], "Only password provider expected in Phase 2"
