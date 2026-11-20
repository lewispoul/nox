# GasCalc · module NOx

Ouvrir `index.html`, ou utiliser `/ui/gascalc/` depuis l’interface NOx. Le calculateur est autonome et ne charge aucune dépendance ni donnée depuis le réseau. Le lien de retour NOx suppose un accès via le serveur local NOx.

## Fonctionnalités

- 503 entrées, 665 séries : Antoine/Poling (325), DIPPR 101/Perry (340).
- Pression de vapeur depuis température et inversion dans le domaine publié.
- Neuf unités de pression absolue, courbe, tables et exports CSV/JSON avec provenance.
- Estimation Clausius–Clapeyron à enthalpie constante, choix de groupes approximatifs Mozga, calibration sur deux points et transfert depuis une corrélation tabulée.

Cette intégration ne lie pas encore les calculs à une expérience ou à un échantillon NOx. Les calculs/export restent dans le navigateur; aucune sauvegarde dans l’API n’est annoncée.

## Données et limites

Les séries existantes proviennent des compilations Poling (2001) et Perry (2008) distribuées par Chemicals. La date de récupération (19 novembre 2026) n’est pas la date des mesures. NIST/DIPPR/ThermoML sont documentés comme sources possibles dans `SOURCES.md`; aucune mise à jour automatique depuis ces services n’est effectuée.

Les coefficients utilisent K et Pa. Antoine utilise un logarithme décimal, DIPPR 101 un logarithme naturel. Les domaines tabulés sont respectés : aucune extrapolation des corrélations publiées. La calibration Clausius–Clapeyron reste une approximation et ne crée pas une incertitude connue. Les quatre chiffres significatifs affichés ne constituent pas une précision garantie.

La base est essentiellement consacrée aux corps purs; l’entrée « Air » est une représentation pseudo-composant, pas un modèle de mélange ni un calcul d’équilibre multicomposant. Aucun azéotrope ou mélange utilisateur n’est calculé. La plage d’une corrélation ne garantit pas la stabilité de la phase liquide ni l’absence de décomposition. La température du bain d’un rotavap n’est pas celle du liquide.

Le PDF Stull personnel et le premier wrapper RMN externe ne sont pas inclus. Les données et leur licence sont conservées dans les fichiers JSON/TSV et `LICENSE-donnees.txt`. Le code original du site Witek Mozga n’est pas repris.

## Validation

Depuis ce dossier :

```bash
node tests.cjs
node integration-tests.cjs
```

Le premier contrôle 13 965 points, monotonie, inversion P↔T, domaines, pressions invalides, quelques points d’ébullition de référence et calibration. Le second exécute les interactions des unités, des groupes, du transfert de calibration et des erreurs dans un DOM simulé. Ce n’est pas une validation métrologique des données, ni un essai tactile réel.
