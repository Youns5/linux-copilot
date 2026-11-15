# Configuration

Les préférences de l'utilisateur sont lues et enregistrées dans
`$XDG_CONFIG_HOME/linux-copilot/config.toml` (par défaut
`~/.config/linux-copilot/config.toml`). Le fichier peut être créé ou modifié sans
changer le code. En son absence, les valeurs par défaut sont utilisées. Les
modifications sont atomiques et le fichier est limité aux permissions `0600`.

```toml
[app]
name = "Linux Copilot"
version = "0.2.0"

[preferences]
language = "fr" # fr, en ou auto

[preferences.display]
colors = true
layout = "detailed" # compact ou detailed
show_explanations = true
show_sources = true
detail_level = "normal" # brief, normal ou detailed

[preferences.ai]
enabled = false
provider = "ollama"
mode = "local" # local, ollama ou auto
model = ""
max_tokens = 2048
temperature = 0.2

[preferences.security]
confirmation_required = true
prudence = "high" # low, standard ou high
show_warnings = true
allow_command_execution = false
```

La langue `auto` reconnaît les locales françaises et anglaises; les autres sont
ramenées au français. La confirmation des opérations sensibles est toujours
obligatoire et ne peut pas être désactivée (ni par fichier, ni par CLI :
`copilot config set security.confirmation_required false` est refusé).
`allow_command_execution` est une préférence future; Linux Copilot n'exécute
actuellement aucune commande. `prudence` est enregistrée mais reste réservée à
de futurs affichages; les avertissements de sécurité sont toujours montrés.
Ne stockez jamais de mot de passe, clé API ou jeton dans le fichier.

Les fonctions `load_preferences`, `set_preference` et `reset_preferences` sont
disponibles depuis `linux_copilot.core`.

## Modes IA

Les modes IA sont `local` (snippets uniquement, IA désactivée), `ollama`
(Ollama local demandé) et `auto` (Ollama si prêt, sinon snippets). L'IA reste
désactivée par défaut; le fournisseur Ollama n'est contacté que si elle est
activée. Aucune API distante ni clé n'est prise en charge.

- `copilot ai enable` : active l'IA en mode `auto`.
- `copilot ai disable` : désactive l'IA (le mode mémorisé est conservé).
- `copilot ai mode ollama` ou `copilot ai mode auto` : enregistre le mode
  **et** active l'IA.
- `copilot ai mode local` : enregistre le mode **et** désactive l'IA.

En cas d'indisponibilité d'Ollama, une notice explicite est affichée et la
recherche par snippets continue; le repli est automatique et silencieux pour
l'utilisateur, les erreurs restant lisibles. Les commandes de gestion sont
documentées dans le README.
