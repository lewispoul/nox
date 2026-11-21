# NOx — validation du premier lot

## Revalidation Windows du 20 novembre 2026

Branche de réparation : `codex/pilot-ci-baseline-20261120`, depuis le pilote
`d2b1d47541f9713fe97a596caaadcd250cbd6ef5`. Python 3.12.12, Node 26.13.1.
Les 27 tests Python, les deux suites UI Node, les 13 965 points GasCalc,
le DOM simulé, les 8 192 comparaisons FID et la démo de six opérations passent.
Black 26.10.1 et Flake8 7.4.1 passent sur `chemlab tests/chemlab`.
Un avertissement de dépréciation Starlette/AnyIO reste présent.

Le test de courses UI échouait avant correction sur un checkout Windows CRLF :
son instrumentation cherchait uniquement LF. Il normalise maintenant les fins
de ligne dans la VM et vérifie explicitement LF et CRLF sans changer le script
livré. Le workflow pilote ajoute Windows à Linux, épingle les outils de lint,
et vérifie le style du pilote. Voir le rapport de session du 20 novembre.

Ces résultats locaux ne remplacent pas les résultats CI du nouveau commit.
Les deux anciens workflows de lint globaux restent distincts et leurs dettes
de style ne sont pas désactivées par cette réparation. Aucun test sur téléphone,
aucune validation du traitement RMN complet ni aucun déploiement n'est ajouté.

## Validation historique du 19 novembre

19 novembre 2026, America/Toronto. Base : PR #101,
`aafce6450d91c10e87b5eb201597af62e68c880b`. Validation locale de l'assemblage,
pas une certification du produit ou de l'ensemble historique NOX.

## Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `python -m pytest tests/chemlab -q` | 27 réussites; deux avertissements de dépréciation de dépendances |
| `node tests/chemlab/ui/app.test.cjs` | Réessais notes, double envoi, confirmation et câblage passent |
| `node tests/chemlab/ui/races.test.cjs` | Réponses tardives, cohérence projet/expérience, générations de session et déconnexion pendant envoi passent |
| `node chemlab/web/gascalc/tests.cjs` | 13 965 points : inversion, domaines, références et calibration passent |
| `node chemlab/web/gascalc/integration-tests.cjs` | Contrôles d'interface en DOM simulé passent |
| `npm test --prefix nmr-spike` | 8 192 paires réelles/imaginaires comparées au FID brut, empreinte conservée |
| `git diff --check` | Aucun défaut d'espacement signalé |
| Chromium / Playwright | Lancement impossible : restriction de socket dans l'environnement |

L'intégration Python vérifie l'accès public aux seuls assets `/ui/`, le refus
d'accès sans jeton aux routes de données, l'absence de cache, les limites du
montage statique et le parcours projet → expérience → note → redémarrage sans
doublon. Les données sont fictives. Les tests numériques de GasCalc vérifient
la cohérence du moteur, pas une incertitude métrologique sur tous les composés.

## Revue indépendante

Un agent autre que l'auteur de l'interface a examiné les échanges UI/API :

- une redirection GET `/` inutilisable sans jeton a été retirée; l'entrée est `/ui/`;
- une réponse tardive de liste des projets pouvait rétablir un projet ancien et
  laisser une expérience appartenant à un autre projet; corrigé par gardes de
  contexte/session et invalidation des sélections. La reproduction VM et les
  tests de régression passent avant publication. Le cas connexe où une note
  devient en attente pendant un chargement de projets est également couvert :
  le contexte reste inchangé et le même identifiant de renvoi reste utilisable;
- aucune fuite de données confirmée dans le montage statique examiné.

La revue n'équivaut pas à un audit exhaustif. Le moteur RMN ancien présente des
anomalies connues de zéro-remplissage implicite et décalage d'axe non fini; les
tests les décrivent explicitement au lieu de déclarer le traitement valide.

## Limites explicites

- Aucun essai tactile/visuel réalisé sur le téléphone réel.
- Aucun accès au laptop de l'utilisateur ou validation de son installation.
- API mono-utilisateur en boucle locale uniquement; pas de déploiement LAN.
- Jeton, brouillons non confirmés et clés de renvoi UI en mémoire seulement;
  fermer ou faire évincer la page peut les perdre. La base serveur persiste.
- Notes en brouillon local, appareils simulés, aucune commande matérielle.
- Aucun FID utilisateur/Kemitek, aucune FT/phase/ppm/intégration RMN validée.
- Les licences de la chaîne RMN récente restent à résoudre avant son intégration.
- Aucun corpus privé `thesis_ai`, FindMolecule, Redis réel, XTB réel ou suite
  historique complète NOX exécuté dans ce lot. Les deux échecs NOX préexistants
  restent documentés dans `chemlab/VALIDATION.md`.

Le workflow `.github/workflows/nox-lab.yml` reproduit les contrôles du lot sur
GitHub. Son résultat doit être consulté sur le commit publié; la présence du
fichier ne prouve pas qu'un run a réussi.
