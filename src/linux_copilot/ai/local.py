"""Client Ollama strictement local, basé sur l'API HTTP de la bibliothèque standard."""

from __future__ import annotations

import json
import shutil
import unicodedata
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from linux_copilot.ai.base import AIAnswer, AICommandSuggestion, OllamaModel, OllamaStatus
from linux_copilot.core.errors import CommunicationError, ModelNotFoundError

_MAX_RESPONSE_BYTES = 5 * 1024 * 1024

# Schéma JSON structuré accepté par Ollama (>= 0.5) via "format" objet : la
# génération est contrainte par grammaire et produit exactement les clés
# attendues, au lieu d'un JSON libre que les petits modèles décorent souvent
# de champs supplémentaires.
_RESPONSE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}},
        "commands": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["command", "explanation"],
            },
        },
    },
    "required": ["summary", "steps", "commands"],
}

# Variantes que les petits modèles emploient à la place des clés demandées.
_SUMMARY_ALIASES = {"summary", "texte", "text", "reponse", "answer", "response"}
_STEPS_ALIASES = {"steps", "etapes", "actions"}
_COMMANDS_ALIASES = {"commands", "commandes", "suggestions"}
_COMMAND_ALIASES = {"command", "commande", "cmd"}
_EXPLANATION_ALIASES = {"explanation", "explication", "description", "detail"}

_REPAIR_PROMPT = (
    "Ta réponse précédente n'est pas exploitable. Réponds uniquement avec un objet "
    "JSON valide, sans texte avant ni après, ayant exactement les clés summary "
    "(texte), steps (liste de textes) et commands (liste d'objets command/"
    "explanation). Utilise [] pour une liste vide et reste concis."
)

_FINAL_FORMAT_ERROR = (
    "La réponse IA n'est pas un objet JSON exploitable, même après une seconde "
    "tentative : elle semble tronquée ou hors format. Augmentez ai.max_tokens ou "
    "reformulez la demande; les snippets locaux restent affichés."
)


def _canonical_key(key: object) -> str:
    """Comparer une clé renvoyée par le modèle sans accents ni casse."""
    if not isinstance(key, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", key.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _parse_json_object(content: str) -> dict[str, object]:
    """Extraire un objet JSON d'une réponse, clôtures Markdown comprises."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        while lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise CommunicationError(_FINAL_FORMAT_ERROR) from None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as error:
            raise CommunicationError(_FINAL_FORMAT_ERROR) from error
    if not isinstance(parsed, dict):
        raise CommunicationError("La réponse IA doit être un objet JSON.")
    return parsed


def _normalise_fields(
    structured: dict[str, object],
) -> tuple[str, list[str], list[tuple[str, str]]]:
    """Récupérer summary/steps/commands en tolérant les clés et variantes du modèle.

    Les clés inconnues sont ignorées : elles n'entrent jamais dans AIAnswer,
    qui ne transporte que du texte et des commandes, jamais de source.
    """
    summary = ""
    for key, value in structured.items():
        if _canonical_key(key) in _SUMMARY_ALIASES and isinstance(value, str) and value.strip():
            summary = value.strip()
            break

    steps: list[str] = []
    for key, value in structured.items():
        if _canonical_key(key) in _STEPS_ALIASES and isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    steps.append(item.strip())
                elif isinstance(item, (int, float)) and not isinstance(item, bool):
                    steps.append(str(item))
            break

    commands: list[tuple[str, str]] = []
    for key, value in structured.items():
        if _canonical_key(key) in _COMMANDS_ALIASES and isinstance(value, list):
            for item in value:
                if not isinstance(item, dict):
                    continue
                command = next(
                    (
                        item_value
                        for item_key, item_value in item.items()
                        if _canonical_key(item_key) in _COMMAND_ALIASES
                        and isinstance(item_value, str)
                        and item_value.strip()
                    ),
                    None,
                )
                if command is None or "\n" in command:
                    continue
                explanation = next(
                    (
                        item_value
                        for item_key, item_value in item.items()
                        if _canonical_key(item_key) in _EXPLANATION_ALIASES
                        and isinstance(item_value, str)
                        and item_value.strip()
                    ),
                    "Explication non fournie par le modèle.",
                )
                commands.append((command.strip(), explanation.strip()))
            break
    return summary, steps, commands


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Empêcher l'API locale de rediriger des prompts vers un hôte distant."""

    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _open_local(request: urllib.request.Request, timeout: float):
    return urllib.request.build_opener(_NoRedirectHandler).open(request, timeout=timeout)


class OllamaClient:
    """Communique uniquement avec Ollama sur une adresse loopback."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 3.0) -> None:
        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.path not in {"", "/"}
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("Ollama doit être configuré sur une adresse HTTP locale (loopback).")
        if timeout <= 0:
            raise ValueError("Le délai de connexion doit être positif.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def is_installed() -> bool:
        """Détecter le binaire sans l'exécuter ni lancer de commande système."""
        return shutil.which("ollama") is not None

    def status(self) -> OllamaStatus:
        """Vérifier le binaire, le service HTTP local et les modèles présents."""
        installed = self.is_installed()
        try:
            models = self.list_models()
        except CommunicationError as error:
            return OllamaStatus(installed=installed, running=False, error=str(error))
        return OllamaStatus(installed=installed, running=True, models=models)

    def list_models(self) -> tuple[OllamaModel, ...]:
        """Lister les modèles locaux; les entrées cloud sont ignorées."""
        payload = self._request("GET", "/api/tags", timeout=self.timeout)
        raw_models = payload.get("models")
        if not isinstance(raw_models, list):
            raise CommunicationError("Réponse Ollama invalide lors de la liste des modèles.")
        models: list[OllamaModel] = []
        for item in raw_models:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("model")
            details = item.get("details", {})
            if not isinstance(name, str) or not name or not isinstance(details, dict):
                continue
            if item.get("remote_host") or item.get("remote_model") or name.endswith(":cloud"):
                continue
            size = item.get("size", 0)
            if isinstance(size, bool) or not isinstance(size, int):
                size = 0
            parameter_size = details.get("parameter_size", "inconnue")
            models.append(
                OllamaModel(
                    name=name,
                    size_bytes=size,
                    parameter_size=parameter_size
                    if isinstance(parameter_size, str)
                    else "inconnue",
                )
            )
        return tuple(sorted(models, key=lambda model: model.name.casefold()))

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        timeout: float = 180.0,
    ) -> AIAnswer:
        """Envoyer un échange non-streaming; aucun outil ou exécution n'est exposé.

        La génération demande d'abord un JSON contraint par schéma (Ollama récent),
        se rabat sur le mode JSON simple pour les serveurs plus anciens, puis
        normalise la réponse en tolérant les variantes des petits modèles.
        """
        if not model or model.endswith(":cloud"):
            raise ModelNotFoundError("Un modèle Ollama local doit être sélectionné.")
        options: dict[str, object] = {"num_predict": max_tokens, "temperature": temperature}

        try:
            content = self._generate(model, messages, options, _RESPONSE_SCHEMA, timeout)
        except CommunicationError as error:
            if not _is_server_rejection(error):
                raise
            # Ollama antérieur à la génération structurée : mode JSON simple.
            content = self._generate(model, messages, options, "json", timeout)

        try:
            return self._build_answer(content, model)
        except CommunicationError:
            # Une seule tentative de correction guidée pour les petits modèles.
            repaired = self._generate(
                model,
                [*messages, {"role": "user", "content": _REPAIR_PROMPT}],
                options,
                _RESPONSE_SCHEMA,
                timeout,
            )
            try:
                return self._build_answer(repaired, model)
            except CommunicationError as final_error:
                raise final_error from None

    def _generate(
        self,
        model: str,
        messages: list[dict[str, str]],
        options: dict[str, object],
        response_format: object,
        timeout: float,
    ) -> str:
        """Demander une génération non-streaming et extraire le contenu texte."""
        payload = self._request(
            "POST",
            "/api/chat",
            {
                "model": model,
                "messages": messages,
                "format": response_format,
                "stream": False,
                "options": options,
            },
            timeout=timeout,
        )
        if isinstance(payload.get("error"), str) and payload["error"].strip():
            raise CommunicationError(f"Ollama a signalé une erreur : {payload['error']}")
        message = payload.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise CommunicationError("Ollama a renvoyé une réponse vide ou invalide.")
        return content

    @classmethod
    def _build_answer(cls, content: str, model: str) -> AIAnswer:
        """Valider puis convertir le contenu du modèle en réponse structurée."""
        structured = _parse_json_object(content)
        summary, steps, commands = _normalise_fields(structured)
        if not summary:
            raise CommunicationError("La réponse IA ne contient pas de résumé exploitable.")
        if (
            len(summary) > 12000
            or len(steps) > 8
            or any(len(step) > 2000 for step in steps)
            or len(commands) > 5
            or any(
                len(command) > 2000 or len(explanation) > 4000 for command, explanation in commands
            )
        ):
            raise CommunicationError(
                "La réponse IA ne respecte pas les limites de contenu attendues."
            )
        return AIAnswer(
            text=summary,
            model=model,
            steps=tuple(steps),
            commands=tuple(
                AICommandSuggestion(command, explanation) for command, explanation in commands
            ),
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        *,
        timeout: float,
    ) -> dict[str, object]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        try:
            with _open_local(request, timeout) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:
            if error.code == 404 and path == "/api/chat":
                raise ModelNotFoundError(
                    "Le modèle Ollama sélectionné est absent localement."
                ) from error
            raise CommunicationError(
                f"Ollama a répondu avec le statut HTTP {error.code}."
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise CommunicationError(
                "Le service Ollama local est indisponible ou a dépassé le délai."
            ) from error
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise CommunicationError("La réponse Ollama dépasse la taille maximale autorisée.")
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise CommunicationError("Ollama a renvoyé un JSON invalide.") from error
        if not isinstance(result, dict):
            raise CommunicationError("Réponse Ollama invalide.")
        return result


def _is_server_rejection(error: CommunicationError) -> bool:
    """Reconnaître un refus du format objet par un Ollama trop ancien."""
    cause = error.__cause__
    return isinstance(cause, urllib.error.HTTPError) and cause.code == 500
