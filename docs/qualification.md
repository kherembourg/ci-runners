# Vérifications réellement effectuées

Mis à jour le 23 septembre 2026. Cette page distingue les résultats observés des capacités seulement prévues. Un workflow vert sur `main` ne prouve pas à lui seul que les PR, les forks ou tous les simulateurs fonctionnent.

## État des cinq dépôts

| Dépôt | Dernière vérification `main` observée |
| --- | --- |
| `ci-runners` | [Verify](https://github.com/kherembourg/ci-runners/actions/runs/35847620398) réussi |
| `RefletsDeBonheur` | [CI](https://github.com/kherembourg/RefletsDeBonheur/actions/runs/35847687484) et [politiques de base](https://github.com/kherembourg/RefletsDeBonheur/actions/runs/35847687473) réussies |
| `lebref` | [CI complète](https://github.com/kherembourg/lebref/actions/runs/35847688151) réussie |
| `finance` | [CI complète](https://github.com/kherembourg/finance/actions/runs/35847688312) réussie |
| `KaMPKit` | [Android](https://github.com/kherembourg/KaMPKit/actions/runs/35847688477) et [iOS](https://github.com/kherembourg/KaMPKit/actions/runs/35847688587) réussis |

Le [job Verify d'une PR de `ci-runners`](https://github.com/kherembourg/ci-runners/actions/runs/35874226951) a également réussi dans une VM Linux jetable portant l'étiquette `personal-ci-linux-arm64-pr`. Les tests unitaires couvrent l'admission des PR, y compris celles de forks. **Une PR de fork et la lane macOS PR n'ont pas encore été vérifiées de bout en bout**.

## Mac et limites

- Mac M1 Pro : 8 cœurs CPU, 32 Gio de RAM, macOS 27.0 au moment de la qualification.
- Alimenté sur secteur ; veille désactivée quand le Mac est branché.
- Tart 2.37.0 installé depuis l'archive officielle après vérification SHA-256.
- Softnet 0.23.0 installé depuis le dépôt Homebrew officiel et utilisé pour isoler le réseau des clones.
- Deux VM simultanées au maximum, chacune avec 4 vCPU et 8192 Mio de RAM.

## VM Linux

- Image Ubuntu 24.04 ARM64 : `ghcr.io/cirruslabs/ubuntu:24.04`.
- Runner GitHub Actions ARM64 2.337.0, archive vérifiée par SHA-256.
- Docker Engine 29.1.3 depuis les paquets Ubuntu.
- Dans un clone isolé, `nproc` indiquait 4 cœurs, `free -m` environ 7914 Mio, l'accès HTTPS à GitHub fonctionnait et Docker a lancé `hello-world` en ARM64.
- Le cycle local clone → démarrage → transmission du JIT par stdin → exécution → arrêt → suppression a passé.
- Le [test manuel Linux](https://github.com/kherembourg/ci-runners/actions/runs/35783619253) a validé CPU, mémoire et Docker ; le runner temporaire et son clone ont ensuite été supprimés.
- Lors d'un [ancien run Android de finance](https://github.com/kherembourg/finance/actions/runs/35790257111), l'outil AAPT2 fourni pour Linux n'a pas démarré dans la VM ARM64. Les builds Android sont donc routés vers macOS ARM64 tant que cette chaîne Linux n'est pas qualifiée.

## VM macOS

- Image macOS ARM64 : `ghcr.io/cirruslabs/macos-tahoe-xcode:26.5`.
- Dans la VM : 4 vCPU, 8589934592 octets de mémoire, Xcode 26.5 et Swift 6.3.2.
- Runner GitHub Actions ARM64 2.337.0, archive vérifiée par SHA-256.
- Le [test manuel macOS](https://github.com/kherembourg/ci-runners/actions/runs/35785084902) a validé CPU, mémoire, Xcode et Swift ; le runner temporaire et son clone ont ensuite été supprimés.
- Un simulateur iPhone 17 Pro a démarré dans un clone jetable et terminé `bootstatus` en environ 49 secondes. Les jobs iOS de [KaMPKit](https://github.com/kherembourg/KaMPKit/actions/runs/35786695244) et de [lebref](https://github.com/kherembourg/lebref/actions/runs/35786740613) ont ensuite passé leurs tests Apple Silicon.
- Le [build Android de KaMPKit](https://github.com/kherembourg/KaMPKit/actions/runs/35792825395) a passé avec les outils Android natifs de la VM macOS.
- Les workflows complets de [lebref](https://github.com/kherembourg/lebref/actions/runs/35793479459) et de [finance](https://github.com/kherembourg/finance/actions/runs/35793189870) ont passé sur les runners personnels.

## Capacité et service autonome

Les tests unitaires vérifient qu'un troisième job attend pendant que deux VM occupent la capacité, et qu'un clone orphelin réserve sa place jusqu'à inspection. Lors d'un essai simultané, une [VM Linux](https://github.com/kherembourg/ci-runners/actions/runs/35785204958) et une [VM macOS](https://github.com/kherembourg/ci-runners/actions/runs/35785209188) ont terminé leurs jobs ; les deux clones ont été supprimés. Le LaunchAgent a ensuite admis automatiquement des [jobs Linux](https://github.com/kherembourg/ci-runners/actions/runs/35786415003) et [macOS](https://github.com/kherembourg/ci-runners/actions/runs/35786418676), tous deux réussis.

La GitHub App dédiée est installée. Un jeton d'installation a été vérifié avec accès aux cinq dépôts configurés seulement. La clé privée reste sur le Mac, hors du dépôt public.
