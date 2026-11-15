"""Coordination de la recherche locale et de l'IA Ollama avec repli hors ligne."""

from __future__ import annotations

from dataclasses import dataclass

from linux_copilot.ai.base import AIAnswer, LocalAIProvider, OllamaModel
from linux_copilot.ai.models import MODEL_RECOMMENDATIONS, SystemResources, get_system_resources
from linux_copilot.ai.prompts import build_messages
from linux_copilot.core.errors import CommunicationError, ModelNotFoundError
from linux_copilot.core.preferences import AIPreferences
from linux_copilot.search.engine import CommandSearch, SearchResult


@dataclass(frozen=True, slots=True)
class EngineResponse:
    """Résultats vérifiés et sortie IA conservés dans des champs distincts."""

    results: tuple[SearchResult, ...]
    ai_answer: AIAnswer | None = None
    ai_notice: str | None = None


class CoreEngine:
    """Chercher d'abord localement puis, si demandé, compléter avec Ollama."""

    def __init__(
        self, search: CommandSearch | None = None, ollama: LocalAIProvider | None = None
    ) -> None:
        self.search = search or CommandSearch()
        if ollama is None:
            from linux_copilot.ai.local import OllamaClient

            ollama = OllamaClient()
        self.ollama = ollama

    def respond(
        self,
        query: str,
        *,
        distribution: str | None,
        language: str,
        preferences: AIPreferences,
        category: str | None = None,
        limit: int = 5,
    ) -> EngineResponse:
        """Chercher des snippets compatibles avant toute génération locale."""
        results = self.search.search(
            query, distribution=distribution, category=category, limit=limit
        )
        if not preferences.enabled or preferences.mode == "local":
            return EngineResponse(tuple(results))
        if preferences.provider != "ollama":
            return EngineResponse(
                tuple(results), ai_notice="Aucun fournisseur IA local n'est configuré."
            )

        try:
            status = self.ollama.status()
        except Exception:
            return EngineResponse(
                tuple(results),
                ai_notice="Erreur inattendue du fournisseur IA; seuls les snippets locaux sont affichés.",
            )
        if not status.running:
            return EngineResponse(
                tuple(results),
                ai_notice=status.error or "Ollama est indisponible; résultats locaux affichés.",
            )
        if not status.models:
            return EngineResponse(
                tuple(results), ai_notice="Aucun modèle local Ollama n'est téléchargé."
            )

        available_models = {model.name: model for model in status.models}
        resources = get_system_resources()
        if preferences.model:
            if preferences.model not in available_models:
                return EngineResponse(
                    tuple(results),
                    ai_notice=f"Le modèle local {preferences.model} n'est pas disponible.",
                )
            selected_model = preferences.model
        else:
            selected_model = self._select_model(available_models, resources)
            if selected_model is None:
                return EngineResponse(
                    tuple(results),
                    ai_notice=self._resource_notice(resources, None, None),
                )

        required_ram = self._required_ram(available_models[selected_model])
        if resources.available_ram_gib is None or required_ram is None:
            return EngineResponse(
                tuple(results),
                ai_notice=self._resource_notice(resources, selected_model, required_ram),
            )
        if resources.available_ram_gib < required_ram:
            return EngineResponse(
                tuple(results),
                ai_notice=self._resource_notice(resources, selected_model, required_ram),
            )
        messages = build_messages(
            query,
            distribution=distribution or "inconnue",
            language=language,
            results=results,
        )
        try:
            answer = self.ollama.chat(
                selected_model,
                messages,
                max_tokens=preferences.max_tokens,
                temperature=preferences.temperature,
            )
        except (CommunicationError, ModelNotFoundError) as error:
            return EngineResponse(
                tuple(results), ai_notice=f"IA locale indisponible; repli local : {error}"
            )
        except Exception:
            return EngineResponse(
                tuple(results),
                ai_notice="Erreur inattendue pendant la génération; seuls les snippets locaux sont affichés.",
            )
        return EngineResponse(tuple(results), ai_answer=answer)

    @staticmethod
    def _select_model(available: dict[str, OllamaModel], resources: SystemResources) -> str | None:
        if resources.available_ram_gib is None:
            return None
        recommendations = {item.name: item for item in MODEL_RECOMMENDATIONS}
        for preferred in ("llama3.2:3b", "qwen2.5:3b", "llama3.2:1b", "qwen2.5:1.5b"):
            recommendation = recommendations[preferred]
            if (
                preferred in available
                and resources.available_ram_gib >= recommendation.minimum_free_ram_gib
            ):
                return preferred
        # Modèle local hors catalogue recommandé : l'estimation prudente à partir
        # de sa taille réelle permet quand même de l'utiliser en mode auto.
        candidates: list[tuple[float, str]] = []
        for name, model in available.items():
            if name in recommendations:
                continue
            estimated = CoreEngine._required_ram(model)
            if estimated is not None:
                candidates.append((estimated, name))
        for estimated, name in sorted(candidates):
            if resources.available_ram_gib >= estimated:
                return name
        return None

    @staticmethod
    def _required_ram(model: OllamaModel) -> float | None:
        for recommendation in MODEL_RECOMMENDATIONS:
            if recommendation.name == model.name:
                return recommendation.minimum_free_ram_gib
        if model.size_bytes <= 0:
            return None
        return max(2.5, (model.size_bytes / 1024**3) * 1.5 + 0.75)

    @staticmethod
    def _resource_notice(
        resources: SystemResources,
        model: str | None,
        required_ram: float | None,
    ) -> str:
        if resources.available_ram_gib is None:
            return "RAM disponible non mesurable; IA non lancée, snippets locaux affichés."
        if model is None:
            return (
                f"RAM disponible : {resources.available_ram_gib:.1f} Gio; aucun modèle local "
                "installé ne correspond aux estimations de ressources. Snippets locaux affichés."
            )
        return (
            f"IA non lancée : {model} demande environ {required_ram:g} Gio de RAM libre selon "
            f"l'estimation Linux Copilot; {resources.available_ram_gib:.1f} Gio sont disponibles. "
            "Snippets locaux affichés."
        )
