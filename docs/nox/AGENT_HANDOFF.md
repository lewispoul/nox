# NOx — reprise par une autre session d'agent

Date : 19 novembre 2026 (America/Toronto).

Une session GitHub/Codex distincte ne reçoit pas automatiquement la conversation
ChatGPT, sa mémoire, les fichiers locaux du laptop ou les messages des agents
lancés ici. Reprendre à partir du dépôt, des PR et des preuves versionnées.

## Lire en premier

1. Cette branche et son parent : `codex/nox-workstreams`, pilote #101.
2. `docs/nox/WORK_PLAN.md` et issue #102 : périmètre, contrats, dépendances.
3. `docs/nox/VALIDATION.md` : tests exécutés et limites.
4. `docs/nox/RUN_LOCAL.md` : installation isolée et interface locale.
5. `docs/nox/NMR_FID_SPIKE.md` : preuve brute et décisions restant ouvertes.
6. `chemlab/PROJECTS.md`, `chemlab/GASCALC.md`, `chemlab/web/README.md`.
7. Les instructions de dépôt réellement applicables, s'il y en a dans la copie
   consultée. Les documents historiques ne prouvent pas l'état d'exécution actuel.

## État transmis

NOx est le nom du projet principal. ChemLab est son domaine laboratoire.
Le premier lot livre des registres projets/expériences, un shell mobile/PC,
notes et journal, GasCalc autonome et une preuve Node de lecture Bruker 1D.
L'API garde un jeton mono-utilisateur, en boucle locale seulement. Les appareils
sont simulés. Les notes restent des brouillons locaux. GasCalc et RMN ne sont
pas encore reliés aux fichiers/résultats d'expérience.

Le FID public est décodé; la FT, l'axe ppm, la phase, les intégrales et le tactile
ne sont pas validés. Le choix d'un moteur actuel doit tenir compte des licences
de toute sa chaîne de dépendances. Ne pas présenter l'ancien wrapper NMRium
hébergé comme un traitement embarqué ou hors ligne.

## Travail de reprise prioritaire

Reproduire les tests isolés du lot. Inspecter les résultats CI actuels et les PR
avant de toucher au code. Sélectionner un seul chantier dans #102 et créer une
branche depuis la base la plus récente validée; ne pas recréer les modules déjà
livrés. Conserver les originaux, identifiants et recettes scientifiques.

La prochaine étape produit utile est le contrat des fichiers/artefacts liés à
une expérience, puis un vrai parcours RMN 1D local validé et des essais sur le
téléphone. Le déploiement réseau et les instruments réels demandent leur propre
lot. Le laptop de l'utilisateur n'a pas été inspecté dans cette session.

## Prompt prêt à coller

```text
Travaille dans le dépôt lewispoul/nox. Le projet principal s'appelle NOx.
Consulte l'issue #102, la PR #101, puis la branche codex/nox-workstreams.
Lis docs/nox/AGENT_HANDOFF.md, WORK_PLAN.md, VALIDATION.md et RUN_LOCAL.md,
ainsi que les instructions du dépôt applicables. Ce dépôt est la source de
contexte; ne présume aucun accès à la mémoire ChatGPT ni au laptop.

Commence par vérifier l'état Git, les PR et les tests du lot. Ne recrée pas les
modules existants. Repère les travaux non terminés et sélectionne une tâche
bornée du prochain jalon : fichiers/artefacts d'expérience ou RMN/FID local,
en respectant les dépendances et les limites de licence documentées.

Implémente sur une nouvelle branche, exécute les vérifications adaptées et
mets à jour l'état du projet avec les commandes et résultats réellement obtenus.
Ouvre explicitement une pull request en brouillon avec problème, changement,
validation et limites. Ne fusionne pas et ne déploie pas. Aucun matériel réel,
aucune donnée Kemitek ni aucun envoi externe ne sont autorisés par ce prompt.
```
