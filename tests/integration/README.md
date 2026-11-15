# Tests d'intégration

`test_offline_stack.py` exécute la CLI complète contre un serveur HTTP Ollama
simulé, éphémère et lié à la boucle locale (`127.0.0.1`, port aléatoire) :

- aller-retour HTTP réel : `/api/tags`, `/api/chat` non-streaming, schéma JSON
  dans la requête, absence d'outils et d'identifiants;
- tolérance aux clés superflues des petits modèles;
- délai dépassé → `CommunicationError`, modèle absent → HTTP 404 →
  `ModelNotFoundError`;
- repli automatique sur les snippets quand le service est arrêté;
- préférences `ai enable|disable|mode|model` isolées via des variables XDG
  temporaires (aucun fichier utilisateur touché);
- flux CLI complets : recherche, catégories, list, config, doctor, aide,
  version, distribution inconnue.

Aucun réseau externe ni modèle réel n'est nécessaire : la suite s'exécute hors
ligne.
