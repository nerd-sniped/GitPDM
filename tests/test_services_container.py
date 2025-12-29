from freecad_gitpdm.core.services import ServiceContainer


class _SettingsStub:
    def __init__(self, host: str, login=None):
        self._host = host
        self._login = login

    def load_github_host(self) -> str:
        return self._host

    def load_github_login(self):
        return self._login


class _Token:
    def __init__(self, access_token: str):
        self.access_token = access_token


class _TokenStoreStub:
    def __init__(self, token):
        self._token = token
        self.calls = []

    def load(self, host, account):
        self.calls.append((host, account))
        return self._token


def test_github_api_client_none_without_host():
    store = _TokenStoreStub(token=_Token("abc"))
    services = ServiceContainer(settings=_SettingsStub(host=""), token_store_factory=lambda: store)

    assert services.github_api_client() is None
    assert store.calls == []


def test_github_api_client_uses_token_store_and_login():
    store = _TokenStoreStub(token=_Token("abc"))
    services = ServiceContainer(
        settings=_SettingsStub(host="github.com", login="octocat"),
        token_store_factory=lambda: store,
    )

    client = services.github_api_client()
    assert client is not None
    assert store.calls == [("github.com", "octocat")]

    # Smoke-check the constructed client has the expected base URL.
    assert getattr(client, "_base_url", "") == "https://api.github.com"
