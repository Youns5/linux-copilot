# Architecture

Le code est organisé en couches : `cli` pour les commandes, `core` pour les
préférences, la configuration, les chemins et l'orchestration, puis des modules
indépendants pour les snippets, la recherche locale, les distributions, la
sécurité et l'IA locale.

La bibliothèque comporte 123 snippets JSON sous `data/snippets/` (14
catégories). Le chargement valide les champs, les identifiants, les
distributions et les sources HTTPS. Le moteur de recherche est déterministe et
fonctionne hors ligne : normalisation des accents, mots fonctionnels écartés,
groupes de synonymes (dont wifi/wi-fi/wireless), filtre de distribution. Les
JSON sont embarqués par setuptools sous `share/linux-copilot/snippets` pour les
installations pip; en mode source, le chargeur lit le dossier du dépôt.

Le `CoreEngine` cherche d'abord les snippets. Si les préférences autorisent
Ollama, le client HTTP local sur loopback complète l'explication : requête
`/api/chat` non-streaming avec un schéma JSON (`summary`, `steps`, `commands`),
repli sur `format: "json"` pour les serveurs plus anciens, normalisation
tolérante des variantes des petits modèles, relance guidée unique en cas de
réponse inexploitable, estimation de RAM avant tout lancement et repli
automatique sur les snippets en cas d'erreur. Les réponses IA sont structurées
sans champ source (les clés inconnues sont ignorées), et les commandes IA sont
analysées puis marquées non vérifiées. Aucune commande ne peut être lancée par
l'application.

La détection de distribution lit `/etc/os-release` sans sous-processus
(Fedora, Debian, Ubuntu, Arch reconnus par ID; toute autre valeur ou un fichier
absent bascule sur des snippets génériques « Linux » avec un avertissement).

La recherche documentaire en ligne, SQLite et le cache documentaire sont des
points d'extension, pas des fonctionnalités disponibles. Le code de production
utilise la bibliothèque standard; pytest et Ruff sont des dépendances de
développement. La suite de tests (92) couvre les modules unitaires et, dans
`tests/integration/`, une CLI complète contre un serveur HTTP Ollama simulé en
boucle locale (génération, tolérance aux clés superflues, délais dépassés,
modèle absent, repli hors ligne, préférences isolées par XDG).
