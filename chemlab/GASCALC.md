# NOx · GasCalc

GasCalc est le module de pression de vapeur et d’ébullition de NOx. Il reprend le calculateur autonome existant en conservant les coefficients, leurs domaines, la provenance, les tests et la licence des données. Il est accessible par `/ui/gascalc/`, servi depuis `chemlab/web/gascalc/index.html`, et utilisable directement dans un navigateur sans réseau.

## Livrable du premier lot

- Nom visible et exports : GasCalc; retour vers l’interface NOx.
- 503 entrées et 665 séries distribuées par Chemicals sous MIT.
- Calculs Antoine et DIPPR 101 dans leur domaine, Clausius–Clapeyron approximatif et calibration deux points.
- Sources/version des compilations et limites d’actualisation documentées.
- Aucun PDF personnel, accès réseau automatique ou wrapper RMN externe distribué.

Les calculs ne sont pas encore rattachés aux expériences et ne sont pas persistés par le serveur. L’interface propre à GasCalc reste autonome. La validation numérique et le DOM simulé ne remplacent pas les essais de navigation sur téléphone.

## Vérifier

```bash
node chemlab/web/gascalc/tests.cjs
node chemlab/web/gascalc/integration-tests.cjs
```

Voir `web/gascalc/README.md`, `SOURCES.md` et `LICENSE-donnees.txt`.
