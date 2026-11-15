# Changelog

## 0.2.0 — 2026-11-15

### Corrigé

- **Génération IA avec Ollama** (bloquant) : la validation exigeait un jeu de
  clés JSON strictement exact (`summary`, `steps`, `commands`), ce que les
  petits modèles comme `qwen2.5:1.5b` ne respectent jamais — toute génération
  échouait avec « La réponse IA contient des champs inconnus ou incomplets ».
  La correction agit à trois niveaux : schéma JSON envoyé à Ollama (génération
  contrainte), repli `format: "json"` pour les serveurs anciens, normalisation
  tolérante (alias de clés, clôtures Markdown, listes absentes, clés inconnues
  ignorées) avec une relance guidée unique avant erreur actionnable.
- Mode `auto` : un modèle local hors catalogue recommandé n'était jamais
  sélectionné même avec assez de RAM.
- `/etc/os-release` absent ou illisible : plus d'erreur bloquante, bascule sur
  les snippets génériques avec avertissement.
- `copilot ai mode ollama|auto` : active désormais réellement l'IA; `mode
  local` la désactive.
- Recherche : « sans » filtré comme mot fonctionnel (correspondances
  parasites), les groupes de synonymes ne réintroduisent plus de mots
  fonctionnels, équivalence wifi/wi-fi ajoutée.
- Sources de snippets : trois URL fausses ou non vérifiables corrigées.
- Délai de génération par défaut porté à 180 s; champ `error` d'Ollama
  signalé; interface fournisseur documentée avec `timeout`.

### Ajouté

- Snippets `network-wifi-scan`, `network-wifi-connect`, `git-undo-last-commit`
  (123 snippets au total, sources officielles vérifiées).
- 15 tests d'intégration avec serveur HTTP Ollama simulé en boucle locale
  (transport, tolérance, délais, repli hors ligne, préférences XDG isolées).
- Métadonnées de paquet (classifiers, mots-clés), formatage `ruff` unifié,
  règles lint `I/B/UP`, journal des changements.

### Modifié

- Version 0.2.0; README réécrit (installation Fedora/Debian/Ubuntu/Arch,
  Ollama, mode hors ligne, sécurité, désinstallation); documentation technique
  mise à jour (`ollama.md`, `security.md`, `configuration.md`,
  `architecture.md`, `audit-finalisation.md`).

## 0.1.0 — version initiale

Moteur local de snippets, détection de distribution, analyse statique de
risque, préférences TOML, intégration Ollama expérimentale.
