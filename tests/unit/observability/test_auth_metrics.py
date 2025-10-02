from adapters.observability.prometheus_client_adapter import PromClientAdapter


class FakeProvider:
    async def authenticate(self, username, password, stored_hash):
        raise Exception("auth failed")


def test_authentication_emits_failure_metric(monkeypatch):
    from auth_core.auth_service import AuthenticationService
    from auth_core.registry import AuthProviderRegistry

    # build a registry that returns a fake provider which raises
    reg = AuthProviderRegistry()
    # monkeypatch registry.get to return a fake provider
    monkeypatch.setattr(reg, "get", lambda name: FakeProvider())

    prom = PromClientAdapter()
    svc = AuthenticationService(registry=reg, metrics_adapter=prom)

    import asyncio

    try:
        asyncio.get_event_loop().run_until_complete(
            svc.login_password(user_id="u1", stored_hash="h", password="p")
        )
    except Exception:
        pass

    out = prom.generate_latest().decode("utf-8")
    assert "auth_failures_total" in out
