"""Façade stable d'accès à la bibliothèque locale de commandes."""

from linux_copilot.snippets.loader import SnippetCatalog, load_catalog
from linux_copilot.snippets.models import Snippet

__all__ = ["Snippet", "SnippetCatalog", "load_catalog"]
