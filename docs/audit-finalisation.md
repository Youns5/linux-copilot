# Rapport d'audit et de finalisation — version 0.2.0

Date : 2026-11-15. Ce rapport documente l'audit complet et les corrections de la
version 0.2.0, qui fait suite à la version initiale 0.1.0.

## Périmètre inspecté

Ensemble des 41 modules Python (`src/`, `tests/`), les 14 puis 17 catalogues
JSON de `data/snippets/`, la documentation `docs/`, `README.md`,
`pyproject.toml`, `requirements.txt` et `.gitignore`. Les 123 snippets ont été
rechargés et validés par le chargeur du projet; les URL de sources incertaines
ont été vérifiées par requête HTTP directe.

## Problème bloquant : la génération IA échouait

**Symptôme.** Ollama actif, modèle présent, `/api/tags` fonctionnel, mais toute
génération terminait sur `CommunicationError: La réponse IA contient des champs
inconnus ou incomplets.`

**Cause racine.** `OllamaClient.chat()` exigeait que le JSON du modèle ait
exactement les clés `{"summary", "steps", "commands"}` (`set(structured) !=
{...}` → erreur), et chaque commande exactement `{"command", "explanation"}`.
Or la requête envoyait seulement `format: "json"` : le modèle — en particulier
un petit modèle comme `qwen2.5:1.5b` — produisait un JSON valide mais agrémenté
de clés supplémentaires (`titre`, `confiance`, `notes`, …) ou de variantes
(`texte`, `commande`), systématiquement rejeté.

**Corrections (à la source, à trois niveaux) :**

1. **Requête** : envoi d'un schéma JSON structuré (`format` objet) qu'Ollama
   (≥ 0.5) transforme en contrainte de grammaire — le modèle ne peut plus
   produire d'autres clés. Repli automatique sur `format: "json"` si le serveur
   répond HTTP 500 (Ollama plus ancien).
2. **Prompt** : le prompt système montre l'objet exact attendu, impose une
   réponse sans texte autour et des listes vides explicites (`[]`).
3. **Validation** : normalisation tolérante — clôtures Markdown retirées, JSON
   extrait d'un éventuel texte englobant, alias de clés acceptés sans accents
   ni casse, listes absentes traitées comme vides, explication manquante
   remplacée par une mention explicite, clés inconnues ignorées (elles
   n'entrent jamais dans l'objet affiché, qui ne transporte aucune source).
   Une relance guidée unique est tentée avant d'abandonner avec un message
   actionnable (augmenter `ai.max_tokens` si la réponse semble tronquée).

Le délai de génération par défaut passe de 120 s à 180 s; le champ `error` que
peut renvoyer Ollama est désormais signalé; l'interface `LocalAIProvider`
documente le paramètre `timeout`.

## Autres corrections

- **Sélection automatique du modèle** (`core/orchestrator.py`) : le mode `auto`
  n'utilisait que les quatre modèles recommandés; tout modèle local hors
  catalogue (par exemple `tinyllama:1.1b`) était ignoré même avec une RAM
  suffisante. Un modèle quelconque est maintenant retenu si l'estimation
  prudente calculée sur sa taille réelle (× 1,5 + 0,75 Gio, minimum 2,5 Gio)
  tient dans la mémoire disponible.
- **Distribution non détectable** (`cli/app.py`) : un `/etc/os-release` absent
  ou illisible remontait une erreur bloquante; il est désormais traité comme
  « distribution inconnue » avec avertissement et snippets génériques.
- **`copilot ai mode`** : `mode ollama`/`auto` active désormais réellement
  l'IA; `mode local` la désactive (auparavant, changer de mode sans `enable`
  ne changeait rien).
- **Recherche** : le mot fonctionnel « sans » n'était pas filtré et provoquait
  des correspondances parasites avec les mots-clés « sans fil » / « sans mot de
  passe » (une requête sans rapport renvoyait jusqu'à 5 résultats); les
  groupes de synonymes ne réintroduisent plus de mots fonctionnels; un groupe
  wifi/wi-fi/wireless/internet a été ajouté et la requête « wifi » renvoie
  désormais le snippet Wi-Fi dédié en tête.
- **Bibliothèque** : ajout de `network-wifi-scan`, `network-wifi-connect` et
  `git-undo-last-commit` (sources officielles vérifiées); correction de trois
  URL de sources qui étaient fausses ou non vérifiables (`rpm-query.8` →
  `rpm.8.html`, miroir Arch pour la page `rsync.1`, page de groupe gcloud
  `config/`). Les 123 snippets passent la validation stricte du chargeur.
- **Qualité** : formatage unifié avec `ruff format` (le projet mélangeait
  tabulations et espaces), imports triés, règles lint étendues (`E4/E7/E9/F/I/B/UP`),
  version 0.2.0 avec métadonnées de paquet complètes.

## Sécurité

- Aucun chemin d'exécution : ni `subprocess`, ni `os.system`, ni shell. Les
  commandes restent des suggestions affichées.
- Le client IA est borné : bouclage HTTP uniquement, sans identifiants, sans
  redirection, réponse plafonnée à 5 Mo, modèles cloud refusés, champ `error`
  signalé.
- Les clés inconnues de la réponse IA (dont d'éventuelles « sources ») sont
  ignorées et jamais affichées; seules les URL des snippets sont présentées
  comme vérifiées.
- Les commandes générées par l'IA sont classées au minimum « moyen », analysées
  statiquement et étiquetées non vérifiées.
- La confirmation des opérations sensibles reste verrouillée (fichier et CLI).

## Vérifications exécutées

- `python -m pytest` : **92 tests** (71 avant) dont 15 tests d'intégration avec
  un serveur HTTP Ollama simulé en boucle locale; tous passent.
- `ruff check .` et `ruff format --check .` : sans erreur.
- Construction d'un wheel `linux_copilot-0.2.0` et installation dans un
  environnement virtuel neuf : les 14 fichiers JSON sont installés sous
  `share/linux-copilot/snippets/`, et toutes les commandes documentées
  (`--help`, `--version`, recherche, `categories`, `list`, `config`,
  `ai status|models|setup|enable|disable|mode|model`, `doctor`) ont été
  exécutées depuis l'installation.
- Génération IA de bout en bout validée contre un serveur simulant la réponse
  réelle d'un petit modèle (clés supplémentaires) : réponse normalisée, commandes
  analysées, aucune erreur.

## Limites de l'environnement d'audit

Ollama n'est pas installé dans l'environnement d'audit : les échanges HTTP ont
été validés contre un serveur simulant fidèlement `/api/tags` et `/api/chat`
(non-streaming, schéma, erreurs 404/500, délais). Le scénario réel
Ollama + `qwen2.5:1.5b` décrit dans le README doit être rejoué sur la machine
cible Fedora 43; d'après les causes identifiées, la correction couvre le défaut
observé (rejet de clés supplémentaires).
