# Format des snippets

Les fichiers JSON versionnes du dossier `data/snippets/` sont charges hors ligne
et inclus dans l'installation du paquet. Chaque fichier contient une liste
d'objets. Le chargeur refuse les champs manquants ou inconnus, les identifiants
dupliques, les sources non HTTPS, les niveaux de risque invalides et les
distributions non prises en charge.

Chaque objet utilise les champs suivants :

- `id`, `title`, `description`, `keywords`, `category`
- `distributions` (`linux`, `fedora`, `debian`, `ubuntu`, `arch`)
- `commands` (lignes a afficher seulement)
- `explanation`, `risk` (`low`, `medium`, `high`), `prerequisites`
- `requires_admin`, `destructive`, `effects`, `sources` (URLs HTTPS)

Un snippet doit utiliser des commandes existantes, une source officielle ou une
page de manuel fiable et decrire les effets visibles. Les commandes de scan
d'hotes distants ou les instructions sans autorisation explicite ne font pas
partie du catalogue. Un besoin de privileges et un niveau de risque sont deux
informations distinctes; les opérations destructrices ne peuvent pas etre
classees a risque faible.