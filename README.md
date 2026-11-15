# Linux Copilot

Linux Copilot est un assistant en ligne de commande pour Linux : vous posez une
question en langage naturel, il propose des commandes adaptées à votre
distribution, avec explication, niveau de risque, prérequis et sources
documentaires. Fedora est la distribution principale ; Debian, Ubuntu et Arch
Linux sont également reconnues.

Deux moteurs coopèrent :

- **Moteur local** : une bibliothèque de 123 snippets JSON vérifiés, consultée
  hors ligne, sans aucune dépendance Python externe ;
- **Moteur IA local (facultatif)** : Ollama avec un modèle local (par exemple
  `qwen2.5:1.5b`). Aucune clé API, aucun abonnement, aucun envoi vers un service
  cloud ; si Ollama est absent ou arrêté, le moteur local prend automatiquement
  le relais.

**Linux Copilot conseille, explique et propose. Il n'exécute jamais de
commande** — ni celles de la bibliothèque, ni celles générées par l'IA.

## Fonctionnalités

- Recherche en langage naturel (`copilot "voir les ports ouverts"`), par mot-clé
  (`copilot search wifi`, `copilot keyword SSH`) et navigation par catégories
  (`copilot categories`, `copilot list Réseau`).
- Pour chaque résultat : commande, explication, compatibilité de distribution,
  analyse statique de risque (privilèges, suppression, écriture, pipelines
  distants), prérequis, effets et sources officielles.
- IA locale Ollama : statut, liste des modèles, sélection, modes `local`,
  `ollama` et `auto`, génération structurée (résumé, étapes, commandes) avec
  repli hors ligne automatique.
- Diagnostic `copilot doctor` : Python, configuration, bibliothèque,
  distribution, paquet installé, Ollama.
- Préférences persistées dans `~/.config/linux-copilot/config.toml` (écriture
  atomique, permissions 0600).
- Fonctionne sans réseau : aucun appel sortant n'est effectué, hormis vers
  l'API Ollama locale `http://127.0.0.1:11434` quand l'IA est activée.

## Prérequis

- Python **3.11 ou plus récent** (testé jusqu'à Python 3.14).
- Linux : Fedora (cible principale), Debian, Ubuntu ou Arch Linux. Une autre
  distribution reste utilisable : seuls les snippets génériques « Linux » sont
  alors proposés.
- Aucune dépendance Python à l'exécution ; pytest et ruff sont facultatifs et
  réservés au développement.
- Ollama uniquement si vous voulez l'IA locale.

## Installation sur Fedora

```bash
sudo dnf install python3-pip git
cd ~/Projets/linux-copilot          # dossier extrait de l'archive
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
copilot --version
```

L'installation `editable` (`-e`) relie le point d'entrée `copilot` au code du
dossier ; les snippets sont lus directement dans `data/snippets/`.

## Installation sur Debian et Ubuntu

```bash
sudo apt update
sudo apt install python3-venv python3-pip
cd ~/Projets/linux-copilot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
copilot --version
```

## Installation sur Arch Linux

```bash
sudo pacman -S python-pip
cd ~/Projets/linux-copilot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
copilot --version
```

Installation sans cloner un dépôt : décompressez `linux-copilot-final.zip`,
placez-vous dans le dossier créé, puis suivez les mêmes commandes (`python -m
venv .venv`, activation, `pip install -e ".[dev]"`). Sans l'extra `dev`,
`pip install -e .` suffit pour un usage quotidien.

## Configuration de l'environnement virtuel

L'environnement `.venv` isole le paquet du Python système. Il doit être activé
dans chaque terminal :

```bash
source .venv/bin/activate
```

Pour rendre la commande `copilot` disponible partout sans activer le venv,
ajoutez un alias dans `~/.bashrc` :

```bash
alias copilot="$HOME/Projets/linux-copilot/.venv/bin/copilot"
```

## IA locale avec Ollama

### Installation d'Ollama

Linux Copilot n'installe jamais de logiciel. Installez Ollama vous-même, par
exemple avec la méthode officielle (<https://ollama.com/download/linux>) :

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Sur Arch Linux, le paquet des dépôts officiels convient aussi :

```bash
sudo pacman -S ollama
systemctl enable --now ollama
```

Vérifiez que le service local répond : `curl -s http://127.0.0.1:11434/api/tags`.

### Téléchargement d'un modèle

Choisissez un modèle adapté à votre RAM et téléchargez-le **manuellement** :

```bash
copilot ai models            # estimations de taille et de RAM + fiche officielle
ollama pull qwen2.5:1.5b     # environ 986 Mo; adapté aux machines modestes
ollama pull llama3.2:3b      # environ 2,0 Go; qualité supérieure si la RAM le permet
```

### Activation de l'IA

```bash
copilot ai enable            # active l'IA en mode auto
copilot ai status            # binaire, service, modèle, état de l'IA
copilot ai model qwen2.5:1.5b   # fixe le modèle local utilisé
copilot ai mode ollama       # toujours utiliser Ollama (snippets si indisponible)
copilot ai mode auto         # Ollama s'il est prêt, sinon snippets
copilot ai mode local        # snippets uniquement (IA désactivée)
copilot ai disable           # désactive l'IA
copilot ai setup             # rappel des étapes manuelles
```

Une fois activée, posez simplement votre question :

```bash
copilot "voir les ports ouverts"
```

Les snippets vérifiés restent affichés en premier ; la réponse IA apparaît
ensuite, marquée « non vérifiée », et ses commandes sont analysées statiquement
puis étiquetées. La génération demande à Ollama un JSON contraint par schéma ;
les clés superflues ou les variantes produites par les petits modèles sont
normalisées, et une tentative de correction est faite avant d'abandonner.

## Commandes

```text
copilot --help                          Aide complète
copilot --version                       Version installée
copilot "voir les ports ouverts"        Recherche en langage naturel
copilot search wifi                     Alias de recherche
copilot keyword SSH                     Recherche par mot-clé (plus de résultats)
copilot categories                      Liste des catégories
copilot list Réseau                     Snippets d'une catégorie
copilot list                            Toutes les catégories
copilot --category Réseau "ports"       Filtre par catégorie
copilot --limit 3 "disque plein"        Limite le nombre de résultats
copilot ai status | models | model | setup | enable | disable | mode
copilot config show | set CLÉ VALEUR | reset
copilot doctor                          Diagnostic de l'installation
```

## Mode hors ligne

Sans Ollama (absent, arrêté ou sans modèle), Linux Copilot continue de
fonctionner normalement : les recherches, catégories, listes et le diagnostic
restent disponibles, aucun plantage ne survient. En mode `auto` ou `ollama`,
une notice explique pourquoi l'IA n'a pas été sollicitée (« service
indisponible », « aucun modèle local », « RAM insuffisante selon l'estimation »)
et les snippets locaux sont affichés. Le retour au moteur local est
automatique ; `copilot doctor` résume l'état de chaque composant.

## Gestion des erreurs

- Les erreurs attendues sont traduites en messages clairs en français :
  configuration invalide, distribution inconnue (les snippets génériques
  restent proposés), modèle absent, délai dépassé, service arrêté.
- Un modèle qui répond hors format déclenche une relance guidée, puis une
  erreur explicite suggérant d'augmenter `ai.max_tokens` ou de reformuler.
- `copilot doctor` et `copilot ai status` indiquent précisément quel composant
  est défaillant ; le code de sortie est non nul en cas d'échec.
- Un journal rotatif est écrit dans `~/.cache/linux-copilot/logs/` avec masquage
  automatique des mots de passe et jetons éventuels.

## Sécurité

- **Aucune exécution** : le code ne contient ni `subprocess`, ni `os.system`,
  ni appel de shell ; les suggestions restent du texte à copier soi-même.
- L'IA ne reçoit aucun outil et ne peut rien déclencher ; ses réponses sont
  séparées des sources vérifiées, ses clés supplémentaires (dont d'éventuelles
  « sources » inventées) sont ignorées, jamais affichées.
- Chaque commande affichée passe par une analyse statique prudente (sudo,
  suppression, formatage, écriture distante, syntaxe composée) et les
  commandes générées par l'IA sont classées au minimum « moyen ».
- Le client IA est limité aux adresses de bouclage (`127.0.0.1`, `localhost`,
  `::1`) en HTTP, sans identifiants, sans redirection, avec des délais bornés
  et une taille de réponse plafonnée ; les modèles « cloud » d'Ollama sont
  refusés.
- La confirmation avant opération sensible est une préférence verrouillée et
  aucune préférence n'ajoute de chemin d'exécution.
  Voir [`docs/security.md`](docs/security.md).

## Lancement des tests

```bash
source .venv/bin/activate
python -m pytest            # 92 tests unitaires et d'intégration
ruff check .                # lint
ruff format --check .       # formatage
```

Les tests d'intégration simulent l'API Ollama sur un serveur HTTP local
éphémère : aucun réseau externe, aucun modèle réel requis. Le scénario réel
Ollama + `qwen2.5:1.5b` doit être validé sur votre machine Fedora selon la
section « IA locale » ci-dessus.

## Désinstallation

```bash
pip uninstall linux-copilot      # dans le venv utilisé
rm -rf ~/.config/linux-copilot   # préférences
rm -rf ~/.local/share/linux-copilot
rm -rf ~/.cache/linux-copilot    # caches et journal
rm -rf .venv                     # si vous supprimez l'environnement
```

## Documentation technique

- [`docs/architecture.md`](docs/architecture.md) — organisation du code.
- [`docs/ollama.md`](docs/ollama.md) — intégration Ollama détaillée.
- [`docs/configuration.md`](docs/configuration.md) — fichier de préférences.
- [`docs/security.md`](docs/security.md) — principes de sécurité.
- [`docs/snippets-format.md`](docs/snippets-format.md) — contribuer un snippet.
- [`docs/audit-finalisation.md`](docs/audit-finalisation.md) — audit et
  corrections de la version 0.2.0.
- [`CHANGELOG.md`](CHANGELOG.md) — historique des versions.

## Licence

Aucune licence n'a encore été choisie ; elle devra l'être avant publication.
