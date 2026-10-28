"""Connection configuration tests; no Atlas account is contacted."""
from unittest.mock import MagicMock
import pytest
import database


def test_uri_is_required(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
    with pytest.raises(RuntimeError, match="Set MONGODB_URI"):
        database.setup_database()
    assert database.client is None


def test_configured_client_is_pinged_and_reused(monkeypatch):
    client = MagicMock()
    factory = MagicMock(return_value=client)
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27099")
    monkeypatch.setattr(database, "MongoClient", factory)
    database.setup_database("pets")
    assert factory.call_args.args == ("mongodb://localhost:27099",)
    assert factory.call_args.kwargs["server_api"].version == "1"
    client.admin.command.assert_called_once_with("ping")
    assert database.db is client["pets"]
    database.close_connection()
    client.close.assert_called_once()


def test_failed_ping_closes_client(monkeypatch):
    client = MagicMock()
    client.admin.command.side_effect = RuntimeError("unavailable")
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27099")
    monkeypatch.setattr(database, "MongoClient", lambda *a, **k: client)
    with pytest.raises(RuntimeError, match="unavailable"):
        database.initialize()
    client.close.assert_called_once()
    assert database.client is None
