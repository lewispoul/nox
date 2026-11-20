# Sources complémentaires et actualisation

Vérification documentaire : 19 novembre 2026 (Québec). La date de consultation d’une base ne constitue pas la date d’une mesure. Aucune nouvelle donnée de ces services n’est importée dans cette version. Les 665 séries existantes proviennent des compilations Poling et Perry distribuées par Chemicals, et non de la transcription du PDF Stull.

| Source | Utilité | Limite |
|---|---|---|
| [NIST Chemistry WebBook](https://webbook.nist.gov/chemistry/guide/) | Coefficients Antoine, domaines de température, références par série; premier choix pour compléter rapidement des solvants ciblés | Certaines séries citent encore Stull (1947); vérifier la référence originale, pas seulement le portail |
| [NIST ThermoData Engine](https://www.nist.gov/mml/acmd/trc/thermodata-engine) | Évaluation thermodynamique avec traçabilité des données | Accès et redistribution selon les conditions du produit; ne pas présumer une base libre téléchargeable |
| [DIPPR Project 801](https://www.aiche.org/dippr/projects/801) | Banque évaluée, publications périodiques | Sous licence; les versions membres et commerciales n’ont pas le même calendrier ni la même couverture temporelle. Les coefficients Perry existants ne sont pas un abonnement DIPPR actuel |
| [NIST ThermoML](https://trc.nist.gov/ThermoML/) | Mesures expérimentales structurées XML/JSON et références | L’archive publique décrite couvre des données jusqu’à 2019, extraction 2020; ce n’est pas un flux continu de mesures récentes |
| [Chemicals](https://chemicals.readthedocs.io/chemicals.vapor_pressure.html) | Intégration numérique et jeux de coefficients redistribuables selon licence | Une bibliothèque mise à jour ne rajeunit pas les mesures de ses compilations |

Pour une future série : conserver CAS, phase, référence bibliographique originale, année de mesure ou publication si disponible, équation, base logarithmique, unités natives, conversion, Tmin/Tmax, incertitude publiée, date de récupération et droits de redistribution. Ne pas fusionner les coefficients de plusieurs séries. Ne pas attribuer une incertitude inventée.
