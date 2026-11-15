"""Tests d'intégration : serveur HTTP Ollama simulé sur 127.0.0.1 et CLI isolée.

Aucun réseau externe : le serveur fictif écoute sur la boucle locale et la
configuration utilisateur est redirigée vers un dossier temporaire via XDG.
"""

import http.server
import json
import socket
import socketserver
import threading

import pytest

from linux_copilot import cli
from linux_copilot.ai.local import OllamaClient
from linux_copilot.core import orchestrator as orchestrator_module
from linux_copilot.core.errors import (
    CommunicationError,
    ModelNotFoundError,
    UnknownDistributionError,
)
from linux_copilot.core.orchestrator import CoreEngine
from linux_copilot.core.preferences import AIPreferences, load_preferences
from linux_copilot.search.engine import CommandSearch
from linux_copilot.snippets.loader import load_catalog

VALID_CONTENT = json.dumps(
    {
        "summary": "Utilisez ss pour lister les sockets en écoute.",
        "steps": ["Lisez la colonne Local Address:Port."],
        "commands": [
            {"command": "ss -tuln", "explanation": "Affiche les sockets TCP et UDP en écoute."}
        ],
    },
    ensure_ascii=False,
)


class _OllamaHandler(http.server.BaseHTTPRequestHandler):
    """Répondre comme l'API Ollama locale, d'après le script du serveur de test."""

    def do_GET(self) -> None:  # noqa: N802 (API http.server)
        if self.path == "/api/tags":
            self._reply(self.server.tags_payload)
        else:
            self._reply({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        self.server.requests.append(body)
        if self.path == "/api/chat":
            models = self.server.tags_payload.get("models", [])
            known = {item.get("name") for item in models}
            if body.get("model") not in known:
                # Comportement réel d'Ollama : un modèle absent répond 404.
                self._reply({"error": "model not found"}, status=404)
                return
            if self.server.chat_responses:
                payload, delay = self.server.chat_responses.pop(0)
                if delay:
                    self.server.sleep_hook(delay)
                self._reply(payload)
            else:
                self._reply({"error": "no scripted response"}, status=500)
        else:
            self._reply({"error": "not found"}, status=404)

    def _reply(self, payload: dict, *, status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args) -> None:  # silencieux
        pass


class _MockOllamaServer(socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, handler):
        super().__init__(("127.0.0.1", 0), handler)
        self.tags_payload: dict = {"models": []}
        self.chat_responses: list[tuple[dict, float]] = []
        self.requests: list[dict] = []
        self.sleep_hook = threading.Event().wait

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"


@pytest.fixture()
def ollama_server():
    server = _MockOllamaServer(_OllamaHandler)
    server.tags_payload = _model_payload()  # un Ollama avec qwen2.5:1.5b installé
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def _model_payload() -> dict:
    return {
        "models": [
            {
                "name": "qwen2.5:1.5b",
                "model": "qwen2.5:1.5b",
                "size": 986061892,
                "details": {"parameter_size": "1.5B"},
            }
        ]
    }


def _client(server: _MockOllamaServer) -> OllamaClient:
    return OllamaClient(base_url=server.base_url)


def _chat_payload(content: str) -> dict:
    return {"message": {"role": "assistant", "content": content}, "done": True}


def test_real_http_roundtrip_detects_models_and_generates(ollama_server) -> None:
    ollama_server.tags_payload = _model_payload()
    ollama_server.chat_responses = [(_chat_payload(VALID_CONTENT), 0.0)]
    client = _client(ollama_server)

    status = client.status()
    assert status.running and status.installed is not None
    assert status.models[0].name == "qwen2.5:1.5b"

    answer = client.chat(
        "qwen2.5:1.5b",
        [{"role": "user", "content": "voir les ports ouverts"}],
        max_tokens=200,
    )
    assert answer.model == "qwen2.5:1.5b"
    assert "ss" in answer.text
    request = ollama_server.requests[-1]
    assert request["model"] == "qwen2.5:1.5b"
    assert request["stream"] is False
    assert request["format"]["type"] == "object"
    assert "tools" not in request


def test_http_roundtrip_tolerates_small_model_extra_keys(ollama_server) -> None:
    # Les petits modèles ajoutent des clés : elles sont ignorées, pas fatales.
    messy = json.dumps(
        {
            "summary": "Diagnostic.",
            "steps": [],
            "commands": [],
            "titre": "Ports",
            "confiance": 0.8,
        },
        ensure_ascii=False,
    )
    ollama_server.chat_responses = [(_chat_payload(messy), 0.0)]

    answer = _client(ollama_server).chat("qwen2.5:1.5b", [{"role": "user", "content": "x"}])
    assert answer.text == "Diagnostic."


def test_http_roundtrip_maps_timeouts_and_unknown_models(ollama_server) -> None:
    client = _client(ollama_server)
    ollama_server.chat_responses = [(_chat_payload(VALID_CONTENT), 1.0)]

    with pytest.raises(CommunicationError, match="délai"):
        client.chat("qwen2.5:1.5b", [{"role": "user", "content": "x"}], timeout=0.2)

    with pytest.raises(ModelNotFoundError, match="absent localement"):
        client.chat("missing:latest", [{"role": "user", "content": "x"}])


def test_engine_falls_back_to_snippets_when_service_is_down(tmp_path, monkeypatch) -> None:
    # Port localement réservé puis refermé : le service est joignable nulle part.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        free_port = sock.getsockname()[1]
    client = OllamaClient(base_url=f"http://127.0.0.1:{free_port}")

    status = client.status()
    assert not status.running
    assert status.error

    results = CoreEngine(CommandSearch(load_catalog()), client).respond(
        "voir les ports ouverts",
        distribution="fedora",
        language="fr",
        preferences=AIPreferences(enabled=True, mode="auto"),
    )
    assert results.results
    assert results.ai_answer is None
    assert "indisponible" in (results.ai_notice or "")


def _isolate_user_config(monkeypatch, tmp_path) -> None:
    for variable in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        monkeypatch.setenv(variable, str(tmp_path / variable.lower()))
    monkeypatch.chdir(tmp_path)


def test_cli_ai_enable_status_and_mode_persist_in_isolated_config(
    monkeypatch, tmp_path, capsys, ollama_server
) -> None:
    _isolate_user_config(monkeypatch, tmp_path)
    ollama_server.tags_payload = _model_payload()
    monkeypatch.setattr(cli.commands, "OllamaClient", lambda: _client(ollama_server))

    assert cli.app.main(["ai", "enable"]) == 0
    preferences = load_preferences()
    assert preferences.ai.enabled and preferences.ai.mode == "auto"

    assert cli.app.main(["ai", "mode", "ollama"]) == 0
    assert load_preferences().ai.mode == "ollama"
    assert load_preferences().ai.enabled

    assert cli.app.main(["ai", "mode", "local"]) == 0
    assert load_preferences().ai.mode == "local"
    assert not load_preferences().ai.enabled

    assert cli.app.main(["ai", "enable"]) == 0
    assert cli.app.main(["ai", "model", "qwen2.5:1.5b"]) == 0
    assert load_preferences().ai.model == "qwen2.5:1.5b"

    assert cli.app.main(["ai", "status"]) == 0
    output = capsys.readouterr().out
    assert "Service local : actif" in output
    assert "qwen2.5:1.5b" in output


def test_cli_ai_model_rejects_absent_model(monkeypatch, tmp_path, capsys, ollama_server) -> None:
    _isolate_user_config(monkeypatch, tmp_path)
    ollama_server.tags_payload = _model_payload()
    monkeypatch.setattr(cli.commands, "OllamaClient", lambda: _client(ollama_server))

    assert cli.app.main(["ai", "model", "inexistant:7b"]) == 2
    assert "n'est pas un modèle local disponible" in capsys.readouterr().err


def test_cli_query_uses_mock_ollama_end_to_end(
    monkeypatch, tmp_path, capsys, ollama_server
) -> None:
    _isolate_user_config(monkeypatch, tmp_path)
    ollama_server.tags_payload = _model_payload()
    ollama_server.chat_responses = [(_chat_payload(VALID_CONTENT), 0.0)]
    monkeypatch.setattr(
        orchestrator_module,
        "get_system_resources",
        lambda: orchestrator_module.SystemResources(8.0, 16.0, 100.0),
    )
    monkeypatch.setattr(cli.app, "OllamaClient", lambda: _client(ollama_server))
    monkeypatch.setattr(cli.app, "load_preferences", lambda: load_preferences())

    assert cli.app.main(["ai", "enable"]) == 0
    assert cli.app.main(["voir les ports ouverts"]) == 0
    output = capsys.readouterr().out
    assert "Commande : ss -tuln" in output
    assert "Analyse IA locale générée par qwen2.5:1.5b" in output
    assert "Suggestion IA non vérifiée" in output
    assert "ne seront jamais exécutées" in output


def test_cli_query_offline_keeps_working_and_explains(monkeypatch, tmp_path, capsys) -> None:
    _isolate_user_config(monkeypatch, tmp_path)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        free_port = sock.getsockname()[1]
    monkeypatch.setattr(
        cli.app, "OllamaClient", lambda: OllamaClient(base_url=f"http://127.0.0.1:{free_port}")
    )
    monkeypatch.setattr(cli.app, "load_preferences", lambda: load_preferences())

    assert cli.app.main(["ai", "enable"]) == 0
    assert cli.app.main(["voir les ports ouverts"]) == 0
    output = capsys.readouterr().out
    assert "Commande : ss -tuln" in output
    assert "indisponible" in output


def test_cli_config_and_categories_and_list(monkeypatch, tmp_path, capsys) -> None:
    _isolate_user_config(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.app, "load_preferences", lambda: load_preferences())

    assert cli.app.main(["config", "set", "display.layout", "compact"]) == 0
    assert load_preferences().display.layout == "compact"
    assert cli.app.main(["config", "show"]) == 0
    assert "couleurs=True" in capsys.readouterr().out

    assert cli.app.main(["categories"]) == 0
    output = capsys.readouterr().out
    assert "Réseau" in output

    assert cli.app.main(["list", "Réseau"]) == 0
    assert "network-open-ports" in capsys.readouterr().out


def test_cli_help_and_version(monkeypatch, tmp_path, capsys) -> None:
    _isolate_user_config(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exit_info:
        cli.app.main(["--version"])
    assert exit_info.value.code == 0
    assert "0.2.0" in capsys.readouterr().out

    with pytest.raises(SystemExit) as exit_info:
        cli.app.main(["--help"])
    assert exit_info.value.code == 0
    assert "aucune commande n'est exécutée" in capsys.readouterr().out


def test_cli_doctor_with_mock_ollama_running(monkeypatch, tmp_path, capsys, ollama_server) -> None:
    _isolate_user_config(monkeypatch, tmp_path)
    ollama_server.tags_payload = _model_payload()
    monkeypatch.setattr(cli.commands, "OllamaClient", lambda: _client(ollama_server))
    monkeypatch.setattr(cli.commands, "load_preferences", load_preferences)

    assert cli.app.main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert "OK Ollama : actif, 1 modèle(s) local(aux)" in output


def test_cli_without_network_and_unknown_distribution(tmp_path, capsys, monkeypatch) -> None:
    _isolate_user_config(monkeypatch, tmp_path)
    monkeypatch.setattr(
        cli.app,
        "detect_system",
        lambda: (_ for _ in ()).throw(
            UnknownDistributionError("Distribution Linux non reconnue : nixos.")
        ),
    )
    monkeypatch.setattr(cli.app, "load_preferences", lambda: load_preferences())

    assert cli.app.main(["voir les ports ouverts"]) == 0
    captured = capsys.readouterr()
    assert "Distribution non reconnue ou non détectable" in captured.err
    assert "ss -tuln" in captured.out
