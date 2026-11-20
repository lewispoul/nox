# NOx — pilotage des travaux

État du 19 novembre 2026, America/Toronto. Projet principal : **NOx**.
Coordination : issue [#102](https://github.com/lewispoul/nox/issues/102).
Base revue : pilote de la PR #101, commit `aafce6450d91c10e87b5eb201597af62e68c880b`.

## Branches et responsabilités du premier lot

| Chantier | Branche | Suivi | Livrable |
|---|---|---|---|
| Intégration et coordination | `codex/nox-workstreams` | #102 | Contrats communs, assemblage, validation et documentation |
| Core | `codex/nox-core-projects` | #103 | Projets et expériences SQLite, API authentifiée, tests |
| Interface mobile/PC | `codex/nox-mobile-ui` | #104 | Connexion, sélection d'expérience, notes et journal |
| GasCalc | `codex/nox-gascalc` | #105 | Calculateur local, provenance et tests numériques |
| RMN/FID | `codex/nox-nmr-fid` | #106 | Preuve de lecture Bruker 1D et décision technique documentée |

Ces branches prolongent #101 et ne remplacent pas `main`. Les PR par module ciblent la branche du pilote `codex/chemlab-local-foundation`
pour permettre une revue isolée. Une PR du lot assemblé cible la même branche
depuis `codex/nox-workstreams`; elle constitue la voie d’intégration proposée.
Choisir cette voie ou les PR unitaires, sans fusionner deux fois le même travail.
Chaque contribution est revue et testée. Les PR restent des brouillons; aucun
merge, publication de service ou accès au laptop n'est implicite dans ce lot.
Les agents peuvent terminer leur tâche; ils ne constituent pas des services
persistants de surveillance après la session.

## Architecture fonctionnelle cible

- Core : projets, expériences, échantillons, identité, permissions, fichiers et journal.
- Assistant et connaissances : recherche sourcée, pont `thesis_ai`, assistance contextuelle.
- Cahier et voix : notes, dictée, brouillons et connecteur FindMolecule à vérifier.
- Instruments et Lab Nodes : capacités universelles, adaptateurs, balances, Pi/ESP32.
- Analyses : RMN/FID, traitement, intégration, prédiction et rapports.
- Calculs : GasCalc, solvants, stœchiométrie et thermodynamique.
- Inventaire et achats : contenants, codes-barres, mesures, stocks et demandes en brouillon.
- Vision et automatisation : observations, règles déterministes et notifications.
- Interface : navigation commune téléphone, PC et poste tactile.
- Exploitation et qualité : installation, sauvegardes, tests et traçabilité.

Les branches fonctionnelles sont une carte du produit. Seuls les quatre chantiers
techniques du tableau sont démarrés dans ce lot, pour limiter les dépendances.

## Contrats du jalon

1. Un projet possède `id` et `name`; une expérience possède `id`, `project_id`, `name`.
2. Les identifiants sont stables et validés. Une répétition identique conserve la
   même entrée; un contenu différent avec le même identifiant retourne 409.
3. Les notes restent `draft_local`. Une confirmation doit provenir de l'API.
   Après une panne ambiguë, l'interface réutilise l'identifiant de la même note.
4. Les observations de ce pilote sont simulées. Aucune commande physique n'est exposée.
5. Les données API nécessitent le jeton commun mono-utilisateur; celui-ci reste
   en mémoire dans l'interface. Aucun service worker ne met les réponses en cache.
6. Les anciens événements peuvent référencer une expérience non enregistrée,
   pour compatibilité avec #101. Le nouveau parcours UI utilise le registre.
7. GasCalc conserve son calcul autonome; ses résultats ne sont pas encore des
   artefacts rattachés aux expériences. RMN/FID reste une preuve technique.

## Ordre de la suite

- Terminer la revue de #101 et du premier lot; fixer les dépendances reproductibles.
- Valider le parcours complet sur PC et téléphone réel, puis préparer un accès
  réseau authentifié/chiffré avant de rendre l'API joignable depuis le téléphone.
- Ajouter des artefacts/fichiers d'expérience non destructifs; brancher GasCalc
  et RMN sur ce contrat commun.
- RMN : valider l'axe, le filtre numérique, FT, phase, référence et intégrales
  contre un logiciel de référence. Conserver FID et recette de traitement.
- Connecter un premier capteur ou une balance en lecture seule, après inventaire
  réel du modèle et de son protocole; passer ensuite au cahier vocal/inventaire.

## Règles d'intégration

Travail borné et revue indépendante. Chaque agent indique les fichiers changés,
les commandes réellement exécutées et les limites restantes. Ne pas reprendre
les affirmations « production ready » des anciennes documentations comme preuve.
Ne pas copier de données Kemitek, corpus privé, secrets, PDF utilisateur ou
fixtures non redistribuables dans le dépôt public. Les essais physiques et les
contrôles temps réel restent distincts du moteur agent et des calculs longs.
