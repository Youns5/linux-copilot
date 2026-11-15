"""Exceptions applicatives avec des messages compréhensibles."""


class LinuxCopilotError(Exception):
    """Erreur de base destinée à être présentée par l'application."""


class ConfigurationError(LinuxCopilotError):
    """Configuration absente, invalide ou illisible."""


class UnknownDistributionError(LinuxCopilotError):
    """Distribution Linux non prise en charge par le détecteur."""


class ResourceNotFoundError(LinuxCopilotError):
    """Fichier ou ressource locale introuvable."""


class ModuleUnavailableError(LinuxCopilotError):
    """Module facultatif indisponible."""


class CommunicationError(LinuxCopilotError):
    """Echec de communication avec un service externe."""


class InternalError(LinuxCopilotError):
    """Erreur interne présentée sans détails techniques sensibles."""


class SystemDetectionError(LinuxCopilotError):
    """Informations système absentes ou mal formées."""


class SnippetValidationError(LinuxCopilotError):
    """Snippet local invalide ou incomplet."""


class ModelNotFoundError(LinuxCopilotError):
    """Modèle demandé absent du catalogue Ollama local."""
