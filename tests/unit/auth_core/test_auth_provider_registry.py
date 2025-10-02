# TEST-AUTH-00: Provider registry exposes only password provider (FR-007, C-036)

def test_default_registry_only_password():
    from auth_core.registry import default_registry
    reg = default_registry()
    names = reg.list_provider_names()
    assert names == ["password"], f"Unexpected providers registered: {names}"
