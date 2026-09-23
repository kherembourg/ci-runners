# Exploitation du runner personnel

Cette page sert à administrer le Mac. Pour comprendre le fonctionnement avant d'utiliser ces commandes, commencer par le [README](../README.md) et la [carte des workflows](workflows.md). Les commandes ci-dessous se lancent **sur le Mac qui héberge les VM**, dans `~/ci-runners`, sauf indication contraire.

## Vérification quotidienne

```sh
python3 -m personal_ci --config config.json doctor
python3 -m personal_ci --config config.json status
launchctl print gui/$(id -u)/dev.personal-ci.runners
```

- `doctor` vérifie que les deux images de base et le fichier de clé GitHub App existent. Il ne lance pas de build et ne garantit pas qu'un workflow applicatif passe.
- `status` affiche le registre des VM réservées. `{}` signifie qu'aucun job n'occupe de VM ; ce n'est pas une erreur.
- `launchctl` doit indiquer `state = running`. Le service ne démarre qu'après ouverture d'une session utilisateur sur le Mac.
- Dans l'onglet **Actions** du dépôt concerné, un job en attente signifie généralement qu'il attend une VM libre. Deux jobs au maximum s'exécutent en parallèle.

Pour distinguer une panne de VM d'une panne propre à un projet, lancer manuellement [Linux VM smoke](../.github/workflows/linux-smoke.yml) ou [macOS VM smoke](../.github/workflows/macos-smoke.yml) depuis GitHub. Ces workflows vérifient CPU, mémoire et outils de base.

## Où sont les données

| Élément | Emplacement | Usage |
| --- | --- | --- |
| Code du contrôleur | `~/ci-runners` | Version Git synchronisée avec `main`. |
| Configuration réelle | `~/ci-runners/config.json` | Liste des dépôts, images, étiquettes et limites ; fichier ignoré par Git. |
| Clé privée GitHub App | `~/.config/personal-ci/github-app.pem` | Reste sur l'hôte, hors du dépôt, permissions `0600`. |
| État et journaux | `~/Library/Application Support/personal-ci/` | `instances.json`, journaux du contrôleur et de chaque VM. |
| Images de base Tart | Tart sur le Mac | `personal-ci-linux-v1` et `personal-ci-macos-v1`, normalement arrêtées. |

Les clones créés pour les jobs sont supprimés en fin d'exécution normale. Si le contrôleur s'arrête brutalement, le registre conserve leur place et demande une inspection avant suppression. Ne jamais supprimer une VM inconnue par une commande globale.

## Préparer un nouvel hôte

Utiliser un Mac Apple Silicon avec 32 Gio de RAM, suffisamment d'espace pour les deux images et deux clones, et au moins **40 Gio libres** après création. Le Mac doit rester alimenté, connecté au réseau et sa session utilisateur ouverte pendant les heures de CI. Le service est un LaunchAgent, pas un daemon disponible avant connexion.

Installer [Tart](https://github.com/openai/tart/releases) depuis une source officielle. Si une archive est utilisée, vérifier sa somme SHA-256 avant extraction. Régler `tart_bin` dans le `config.json` ignoré vers le vrai exécutable. Dans les exemples suivants, `TART_BIN` représente ce chemin :

```sh
TART_BIN="$HOME/.local/opt/tart.app/Contents/MacOS/tart"
"$TART_BIN" list
```

Installer [Softnet](https://github.com/openai/softnet) pour isoler le réseau des clones (`brew install openai/tools/softnet`). Le binaire utilisé par Tart doit être sous `/opt/homebrew/bin`, appartenir à `root` et posséder le bit SUID décrit par le projet. Vérifier la source et le chemin avant de lui donner ce privilège. Sans Softnet, le démarrage des clones de jobs échoue.

Créer deux images de base **arrêtées**. Les versions ci-dessous correspondent aux images qualifiées ; le téléchargement macOS peut représenter des dizaines de gigaoctets. La commande `run` reste ouverte : lancer les commandes `exec` et `stop` dans **un deuxième terminal**.

Linux, terminal A :

```sh
TART_BIN="$HOME/.local/opt/tart.app/Contents/MacOS/tart"
"$TART_BIN" clone ghcr.io/cirruslabs/ubuntu:24.04 personal-ci-linux-v1
"$TART_BIN" set personal-ci-linux-v1 --cpu 4 --memory 8192
"$TART_BIN" run --no-graphics personal-ci-linux-v1
```

Linux, terminal B pendant que la VM tourne :

```sh
TART_BIN="$HOME/.local/opt/tart.app/Contents/MacOS/tart"
"$TART_BIN" exec -i personal-ci-linux-v1 /bin/bash -s < scripts/bootstrap-linux.sh
"$TART_BIN" stop personal-ci-linux-v1
```

macOS, terminal A :

```sh
TART_BIN="$HOME/.local/opt/tart.app/Contents/MacOS/tart"
"$TART_BIN" clone ghcr.io/cirruslabs/macos-tahoe-xcode:26.5 personal-ci-macos-v1
"$TART_BIN" set personal-ci-macos-v1 --cpu 4 --memory 8192
"$TART_BIN" run --no-graphics personal-ci-macos-v1
```

macOS, terminal B pendant que la VM tourne :

```sh
TART_BIN="$HOME/.local/opt/tart.app/Contents/MacOS/tart"
"$TART_BIN" exec -i personal-ci-macos-v1 /bin/bash -s < scripts/bootstrap-macos.sh
"$TART_BIN" stop personal-ci-macos-v1
```

Le bootstrap Linux installe Docker et le runner ARM64 ; celui de macOS vérifie Xcode et installe le runner ARM64. Les archives des runners ont des SHA-256 épinglés dans les scripts. Redémarrer chaque image après préparation pour vérifier les 4 vCPU, la mémoire et les outils, puis la laisser arrêtée. **Ne jamais mettre de jeton ou d'identifiant de runner dans une image de base.**

## Accès à GitHub

Une GitHub App dédiée doit avoir les permissions dépôt **Actions : lecture** et **Administration : lecture/écriture**. Elle n'a besoin ni de webhook ni d'événement souscrit : le contrôleur interroge l'API. La clé privée téléchargée est stockée sur le Mac :

```sh
mkdir -p ~/.config/personal-ci
chmod 700 ~/.config/personal-ci
# Déplacer la clé téléchargée ici, sans l'afficher dans le terminal.
chmod 600 ~/.config/personal-ci/github-app.pem
```

Dans `config.json`, renseigner `repositories`, `github_app.app_id` et `github_app.private_key_file`. Même si l'App est installée sur tout le compte, le contrôleur demande un jeton d'installation limité aux seuls dépôts de `repositories` et à ces deux permissions. La clé et les jetons restent hors des images et des journaux. Le [modèle public](../config.example.json) ne contient aucun secret.

## Démarrer ou diagnostiquer le service

Avant la première installation :

```sh
python3 -m unittest discover -s tests -v
python3 -m personal_ci --config config.json doctor
python3 -m personal_ci --config config.json once
python3 scripts/install-service.py
```

`once` admet les jobs disponibles une seule fois, attend leur fin, puis s'arrête. `install-service.py` installe le LaunchAgent **une seule fois** ; ne pas le relancer sur un hôte déjà installé. Pour inspecter un service existant :

```sh
launchctl print gui/$(id -u)/dev.personal-ci.runners
python3 -m personal_ci --config config.json status
```

Si un job reste en attente, vérifier dans cet ordre : Mac allumé et session ouverte, service `running`, deux places déjà occupées, espace libre (réserve de 40 Gio), étiquette `runs-on` du job, dépôt présent dans `repositories` et accès de l'App. Le contrôleur n'admet que `push`, `workflow_dispatch`, `schedule` et `pull_request` ; il ignore `pull_request_target`.

Si un job échoue, lire d'abord les étapes dans GitHub Actions. En cas de panne d'infrastructure, consulter `controller.err.log`, le journal de la VM indiqué par `instances.json` et la liste Tart. `python3 -m personal_ci --config config.json reconcile` retire les entrées dont le clone n'existe plus et marque les clones orphelins pour inspection. **Inspecter le job GitHub et le clone avant toute suppression manuelle** : le numéro de job utilisé lors de l'admission ne prouve pas à lui seul quel job le runner a reçu.

Les clones utilisent Softnet, sans presse-papiers ni partage de dossier avec l'hôte. Les PR de forks restent du code non fiable ; ne pas leur exposer la clé de l'App, des secrets hôte ou des jetons GitHub en écriture.
