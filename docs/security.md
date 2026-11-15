# Principes de sécurité

- Linux Copilot ne possède aucun mécanisme d'exécution de commande et n'appelle
  ni shell, ni `sudo`, ni sous-processus pour exécuter les suggestions.
- Les snippets affichent leurs risques, prérequis, effets et sources.
- `security.analyzer` analyse les motifs de privilège, suppression, écriture et
  pipelines distants sans interpréter ni lancer le shell. Une absence d'alerte
  n'est jamais une garantie d'innocuité.
- Une commande générée par l'IA reçoit au minimum un risque moyen, une analyse
  statique, une étiquette non vérifiée et ne peut pas être exécutée par le CLI.
- Le modèle ne peut pas injecter de références : la réponse IA est convertie en
  un objet qui ne contient que du texte (résumé, étapes, commandes). Toute clé
  supplémentaire renvoyée par le modèle — y compris des « sources » inventées —
  est ignorée et jamais affichée; seules les URL attachées aux snippets sont
  présentées comme références vérifiées.
- Le client IA n'accepte qu'une adresse de bouclage HTTP (`127.0.0.1`,
  `localhost`, `::1`), sans identifiants ni redirections, avec un délai de
  connexion (3 s) et de génération (180 s par défaut), une taille de réponse
  plafonnée à 5 Mo et le refus explicite des modèles Ollama Cloud.
- Les règles fondamentales ne consultent pas `allow_command_execution`; cette
  préférence n'ajoute aucun chemin d'exécution. La confirmation avant une
  opération sensible est verrouillée : la désactiver est refusée à la fois par
  la CLI et par le chargeur de configuration.

L'analyse statique est volontairement limitée et peut avoir des faux positifs ou
des faux négatifs. Les commandes contenant une syntaxe shell composée demandent
une vérification manuelle de chaque segment.
