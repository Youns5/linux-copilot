# IA locale avec Ollama

Linux Copilot communique uniquement avec l'API HTTP locale Ollama sur
`127.0.0.1:11434`. Il n'envoie ni clé, ni requête à un service distant; le client
utilise la bibliothèque standard Python et des délais bornés. Aucun binaire
système n'est lancé par l'application.

## Installation manuelle

1. Installer Ollama en suivant la page officielle Linux :
   <https://ollama.com/download/linux>.
2. Si le service n'est pas démarré par l'installation, lancer `ollama serve`.
3. Vérifier les estimations avec `copilot ai models`.
4. Après avoir choisi un modèle et confirmé l'espace disque, télécharger un seul
   modèle explicitement, par exemple `ollama pull qwen2.5:1.5b`.
5. Le sélectionner avec `copilot ai model qwen2.5:1.5b`, puis activer l'IA via
   `copilot ai enable`.

Linux Copilot n'exécute aucune de ces commandes et ne télécharge jamais un modèle.
Ollama fonctionne avec ses modèles locaux sans compte ni clé; éviter les modèles
Ollama Cloud pour respecter le mode local.

## Modèles et ressources

Les tailles affichées proviennent des fiches de modèles Ollama : Llama 3.2 3B est
environ 2.0 Go, Qwen2.5 3B environ 1.9 Go; des variantes 1B/1.5B sont aussi
proposées (`qwen2.5:1.5b` : environ 986 Mo). Les besoins de RAM sont des
estimations Linux Copilot, pas des minima garantis. `copilot ai models` lit la
mémoire disponible et l'espace libre du dossier personnel, mais ne détecte pas le
GPU et ne connaît pas forcément le répertoire configuré pour le stockage Ollama.
Vérifier le matériel et le stockage avec la
[documentation GPU Ollama](https://docs.ollama.com/gpu) avant un gros
téléchargement. La vitesse dépend du matériel, de la quantification et des autres
applications ouvertes.

## Modes

- `local` : recherche dans la bibliothèque de snippets uniquement (l'IA est
  automatiquement désactivée).
- `ollama` : demande une explication au modèle local; en cas d'indisponibilité,
  affiche les snippets et un avis.
- `auto` : utilise Ollama s'il répond avec un modèle local, sinon revient aux
  snippets.

`copilot ai enable` active l'IA en mode `auto`; `copilot ai disable` revient à
la recherche seule. `copilot ai mode ollama|auto` active aussi l'IA,
`copilot ai mode local` la désactive. `copilot ai status` vérifie le binaire, le
service et les modèles; `copilot ai model` affiche ou sélectionne un modèle déjà
présent; `copilot ai setup` ne fait qu'afficher les instructions.

Sélection automatique du modèle (quand aucun modèle n'est fixé) : parmi les
modèles recommandés, le premier installé dont l'estimation de RAM entre dans la
mémoire disponible est choisi; à défaut, tout autre modèle local installé est
retenu si l'estimation prudente calculée à partir de sa taille réelle (taille
× 1,5 + 0,75 Gio, minimum 2,5 Gio) tient dans la RAM disponible.

## Pipeline d'une génération

1. La recherche locale sélectionne jusqu'à 5 snippets vérifiés, fournis au
   modèle avec la demande et la distribution détectée.
2. La requête `/api/chat` est envoyée en `stream: false`, sans outils ni
   identifiants, avec `format` = **schéma JSON** (`summary`, `steps`,
   `commands`) : les Ollama récents (≥ 0.5) contraignent la génération par
   grammaire et ne peuvent produire que les clés attendues.
3. Si le serveur rejette le schéma objet (HTTP 500, Ollama plus ancien), la
   requête est relancée en `format: "json"` classique.
4. La réponse est normalisée avec tolérance : clôtures Markdown retirées, clés
   voisines acceptées (`texte`/`reponse` pour `summary`, `etapes` pour
   `steps`, `commande`/`cmd`, `explication`/`description`), listes absentes
   traitées comme vides. Toute clé inconnue est ignorée — elle n'entre jamais
   dans la réponse affichée, qui ne transporte ni source ni métadonnée.
5. Si le contenu n'est pas un JSON exploitable, une relance guidée unique est
   tentée; en cas de nouvel échec, une erreur claire suggère d'augmenter
   `ai.max_tokens` (réponse tronquée) ou de reformuler.
6. Le délai par défaut d'une génération est de 180 s; les dépassements, erreurs
   HTTP et réponses `{"error": ...}` sont convertis en messages applicatifs et
   déclenchent le repli sur les snippets.

Références API officielles : [liste des modèles](https://docs.ollama.com/api/tags)
et [chat](https://docs.ollama.com/api/chat).

## Fiabilité et sécurité

La recherche locale et ses snippets sont affichés en premier avec leurs commandes,
risques, effets et sources. L'IA reçoit uniquement ces extraits et la demande. Sa
réponse est structurée et sans champ de source; les commandes proposées par le
modèle sont analysées statiquement, classées au minimum à risque moyen et
marquées **générées et non vérifiées**. Une consigne de prompt ne constitue pas
une garantie. Aucune sortie du modèle n'est exécutée, et seules les sources
attachées aux snippets sont présentées comme vérifiées.
