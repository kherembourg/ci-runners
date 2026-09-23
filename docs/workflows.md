# Carte des workflows

Cette page décrit l'installation actuelle. Les fichiers de workflow de chaque projet se trouvent dans **son propre dépôt**, sous `.github/workflows/`. Ce dépôt fournit les VM et le contrôleur ; il ne contient pas les tests métier des autres projets. Certains dépôts ci-dessous sont privés : leurs liens ne s'ouvrent qu'avec un accès GitHub adapté.

## Comment lire les tableaux

« Push » signifie qu'un commit arrive sur la branche indiquée. « PR » signifie pull request. « Manuel » correspond au bouton *Run workflow* de GitHub. Une ligne Linux ou macOS désigne une **VM sur le Mac personnel** ; la variante `-pr` est choisie automatiquement pour les PR. Les jobs d'un même workflow peuvent partir en parallèle, dans la limite globale de deux VM. Un job qui dépend d'un autre attend sa fin.

| Événement | Linux | macOS |
| --- | --- | --- |
| Push, horaire ou manuel | `personal-ci-linux-arm64` | `personal-ci-macos-arm64` |
| PR | `personal-ci-linux-arm64-pr` | `personal-ci-macos-arm64-pr` |

Aucun des workflows ci-dessous n'utilise un runner hébergé par GitHub. GitHub reste responsable du déclenchement, de la file, des journaux, des statuts et des artefacts.

## `ci-runners` — ce dépôt

| Workflow | Quand | Ce qu'il fait | VM |
| --- | --- | --- | --- |
| [`verify.yml`](../.github/workflows/verify.yml) | Chaque push et PR | Exécute les tests Python du contrôleur et vérifie la syntaxe des scripts d'installation. | Linux ; Linux PR pour une PR |
| [`linux-smoke.yml`](../.github/workflows/linux-smoke.yml) | Manuel uniquement | Vérifie les 4 vCPU, les 8 Gio de RAM et Docker dans une VM Linux. | Linux |
| [`macos-smoke.yml`](../.github/workflows/macos-smoke.yml) | Manuel uniquement | Vérifie les 4 vCPU, les 8 Gio de RAM, Xcode et Swift dans une VM macOS. | macOS |

Un *smoke test* est un contrôle court qui confirme que l'infrastructure de base fonctionne ; il ne teste pas une application.

## `RefletsDeBonheur`

| Workflow | Quand | Jobs et résultat attendu | VM |
| --- | --- | --- | --- |
| [`ci.yml`](https://github.com/kherembourg/RefletsDeBonheur/blob/main/.github/workflows/ci.yml) | Push sur `main` ou `master`, et PR | Vérification TypeScript et traductions, tests unitaires et d'intégration, build, audit de sécurité, qualité, parcours navigateur Playwright et comparaison des captures visuelles. `publish-coverage` publie la couverture uniquement après un push réussi sur `main`. `all-checks-passed` vérifie les jobs obligatoires ; la qualité est informative. | Linux ; Linux PR pour une PR |
| [`database-isolation.yml`](https://github.com/kherembourg/RefletsDeBonheur/blob/main/.github/workflows/database-isolation.yml) | Push sur `main` ou PR **si** les migrations, tests Supabase ou ce workflow changent | Démarre PostgreSQL comme service Docker et teste les politiques d'isolation de la base. | Linux ; Linux PR pour une PR |
| [`pr-validation.yml`](https://github.com/kherembourg/RefletsDeBonheur/blob/main/.github/workflows/pr-validation.yml) | PR ouverte, modifiée, rouverte ou synchronisée | Cinq petits jobs contrôlent le titre, la description, la taille, le statut brouillon/WIP et les références à des issues. | Linux PR |
| [`scheduled-security.yml`](https://github.com/kherembourg/RefletsDeBonheur/blob/main/.github/workflows/scheduled-security.yml) | Chaque lundi à 09:00 UTC, ou manuel | Audite les dépendances et produit un rapport de sécurité. | Linux |

Les captures de référence Playwright sont des images Linux. Les dix comparaisons visuelles ont passé dans la VM Linux ARM64 sans modifier les images existantes.

## `lebref`

Le [workflow `ci.yml`](https://github.com/kherembourg/lebref/blob/main/.github/workflows/ci.yml) démarre lors d'un push sur `main` ou d'une PR vers `main`.

| Job | Ce qu'il fait | VM |
| --- | --- | --- |
| `server` | Tests du serveur Ktor/JVM et régression de configuration de sécurité. | Linux ; Linux PR |
| `web` | Installation, vérification de types, tests et build Svelte/Vite. | Linux ; Linux PR |
| `desktop` | Tests JVM du code partagé et build de l'application desktop. | macOS ; macOS PR |
| `android` | Tests du code partagé Android et build de l'application Android. | macOS ; macOS PR |
| `ios` | Tests Kotlin pour le simulateur iOS ARM64. | macOS ; macOS PR |

Android utilise macOS parce que la chaîne Android qualifiée sur ce Mac y fonctionne ; le serveur et le web n'ont pas besoin de Xcode.

## `finance`

Le [workflow `ci.yml`](https://github.com/kherembourg/finance/blob/main/.github/workflows/ci.yml) démarre lors d'un push ou d'une PR vers `main`.

| Job | Ce qu'il fait | VM |
| --- | --- | --- |
| `server` | Tests et build du serveur. | Linux ; Linux PR |
| `android` | Tests, couverture Kover et assemblage Android. Pour une PR, calcule l'écart de couverture et tente de commenter la PR ; sur `main`, met à jour le badge. | macOS ; macOS PR |
| `ios` | Compile la cible iOS pour simulateur ARM64. | macOS ; macOS PR |
| `ios-build` | Lance `xcodebuild` pour l'application iOS. Ce job est informatif (`continue-on-error`). | macOS ; macOS PR |

## `KaMPKit`

Deux workflows distincts démarrent sur push vers `main`, PR (avec filtres de chemins) ou lancement manuel.

| Workflow | Ce qu'il fait | VM |
| --- | --- | --- |
| [`KaMPKit-Android.yml`](https://github.com/kherembourg/KaMPKit/blob/main/.github/workflows/KaMPKit-Android.yml) | Prépare Java et le SDK Android, puis lance `./gradlew build`. | macOS ; macOS PR |
| [`KaMPKit-iOS.yml`](https://github.com/kherembourg/KaMPKit/blob/main/.github/workflows/KaMPKit-iOS.yml) | Lance les tests `iosSimulatorArm64Test`, puis construit le projet Xcode sans signature de distribution. | macOS ; macOS PR |

## Ajouter ou modifier un workflow

1. Placer le fichier YAML dans `.github/workflows/` du projet concerné.
2. Choisir Linux pour les tâches web/JVM/Docker et macOS pour Xcode, iOS ou les builds Android actuellement qualifiés.
3. Utiliser l'étiquette PR correspondante pour `pull_request`. Pour un workflow push + PR, les fichiers ci-dessus montrent l'expression `runs-on` à copier.
4. Garder les permissions GitHub minimales et ne pas transmettre de secret à du code provenant d'un fork. Le workflow `finance` demande actuellement une écriture pour ses commentaires et son badge : revoir ce choix si les PR externes deviennent courantes.
5. Vérifier que le dépôt figure dans `repositories` du `config.json` local et dans l'installation de la GitHub App. Le fichier local n'est jamais publié.
6. Lancer un job de test et vérifier dans GitHub le nom du runner, le statut et les journaux. Les [tests manuels de ce dépôt](../.github/workflows) servent à distinguer un problème de VM d'un problème propre au projet.

Pour la préparation des images et le dépannage du service, voir le [guide d'exploitation](operations.md).
