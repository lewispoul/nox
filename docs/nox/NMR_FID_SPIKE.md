# NOx — preuve technique RMN / FID 1D

Date de vérification : 19 novembre 2026 (America/Toronto).
Statut : **décodage brut vérifié sur un FID public; aucun traitement mobile livré**.

## Résultat concret

La preuve `nmr-spike/` lit localement une véritable expérience Bruker d'aspirine,
à partir de `fid` et `acqus` dans un ZIP public. Elle n'appelle ni NMRium hébergé,
ni un modèle de prédiction. Après installation des dépendances et acquisition de
la fixture, le test s'exécute sans téléchargement.

| Contrôle exécuté | Résultat |
| --- | --- |
| ZIP public, SHA-256 connu | 59 987 octets, empreinte vérifiée |
| FID binaire présent, aucun `pdata/1/1r` | 65 536 octets |
| Type vérifié dans les paramètres | 1D, ¹H, BYTORDA=1, DTYPA=0 |
| Paires acquises int32 réel/imaginaire | **8 192**, comparées une par une au binaire big-endian |
| Tableaux produits par nmr-parser | 16 384 points, dont 8 192 zéros ajoutés implicitement |
| Fréquence d'origine lue | 300.132250975 MHz |
| Largeur spectrale d'acquisition lue | 4789.27203065134 Hz |
| Conservation du ZIP source | SHA-256 identique après lecture |
| FT, phase, ppm, intégrales et mobile | **Non validés** |

**Anomalie bloquante pour un usage scientifique direct :** `nmr-parser@3.0.3`
renvoie un `dimensions[0].coordinatesOffset.magnitude` non fini (`NaN`, sérialisé
`null`) sur cette fixture. Le code source emploie `info.fid` alors que la sortie
porte `info.isFid`, et utilise `spectraWidth` plutôt que le `spectralWidth` exposé.
L'axe retourné ne doit donc pas être accepté sans contrôle. L'axe temporel et le
facteur 2 entre dwell time d'une valeur et pas d'une paire complexe doivent aussi
être validés indépendamment. Le test documente l'anomalie; son succès ne constitue
pas une approbation du parseur pour la production.

## Reproduire

Node utilisé : 24.22.3; npm : 11.19.1.

```sh
cd nmr-spike
npm ci --ignore-scripts
npm run fetch-fixture
npm test
```

Les deux premières commandes nécessitent Internet; `npm test` n'utilise pas le
réseau. Le téléchargement utilise une URL de commit fixe, vérifie l'empreinte,
puis écrit une copie locale. Aucun fichier utilisateur n'est utilisé. Les
`node_modules` et le ZIP téléchargé sont ignorés par Git.

Fixture :

- dépôt : https://github.com/cheminfo/bruker-data-test ; licence MIT, copie de la notice dans `nmr-spike/BRUKER_FIXTURE_LICENSE`;
- fichier : `data/zipped/aspirin-1h.zip`;
- commit contenant le fichier : `bb9478262aa3513b64b661ddb2f2697ad86463e6`;
- URL fixe : https://raw.githubusercontent.com/cheminfo/bruker-data-test/bb9478262aa3513b64b661ddb2f2697ad86463e6/data/zipped/aspirin-1h.zip ;
- SHA-256 : `b919359fcac83e5d2ca82d399123a0d4c2a8fe15c7e71937bfe59a4508bab75e`.

## Moteurs et licences : distinctions nécessaires

Métadonnées consultées directement avec `npm view <paquet> version license` et
`npm view nmrium@3.1.0 dependencies --json` :

| Paquet | Version observée | Licence déclarée | Utilisation dans ce lot |
| --- | --- | --- | --- |
| `nmrium` | 3.1.0 | MIT | Étudié; pas installé ni embarqué |
| `nmr-parser` | 3.0.3 | MIT | Preuve Node uniquement |
| `filelist-utils` | 1.11.3 | MIT; paquet déprécié | Preuve Node uniquement |
| `file-collection` | 6.7.0 | MIT | Candidat à évaluer |
| `brukerconverter` actuel | 8.0.3 | CC-BY-NC-SA-4.0 | Non installé directement |
| `nmr-processing` actuel | 22.28.1 | CC-BY-NC-SA-4.0 | Non installé directement |
| `brukerconverter` résolu dans le spike | 5.0.3 | MIT | Dépendance de nmr-parser |
| `nmr-processing` résolu dans le spike | 9.9.2 | MIT | Dépendance de nmr-parser |
| `jszip` | 3.10.1 | MIT OU GPL-3.0-or-later | Preuve, choix de la licence MIT |

Le paquet NMRium 3.1.0 dépend directement de `nmr-processing ^22.25.0`.
**La licence MIT de son enveloppe ne suffit donc pas à conclure que toute la
chaîne est utilisable commercialement sans condition.** Avant intégration à
Kemitek, identifier les versions exactes, les dépendances et les droits adéquats;
choisir une chaîne compatible ou obtenir la licence nécessaire. Le lockfile du
spike fixe une ancienne chaîne MIT pour reproduire l'expérience; ce n'est pas
une recommandation de maintenir ces versions anciennes en production.

Les conditions du site `app.nmrium.com` et les licences de ses composants sont
également distinctes. Une iframe vers ce site nécessite Internet et ne livre
pas un moteur local. Le site actuel documente son accès public; ne pas en déduire
une autorisation pour des données professionnelles confidentielles.

## Architecture cible proposée

- Un adaptateur d'import 1D dans un Web Worker : ZIP utilisateur en mémoire,
  acquisition/endianness/type numérique détectés, taille décompressée bornée.
- Source brute immuable (empreinte), métadonnées d'acquisition normalisées et
  contrôlées; `acquiredPointCount` distinct de `zeroFilledPointCount`.
- Pipeline explicite et rejouable : filtre numérique, apodisation, zero filling,
  FT, phase, ligne de base, référence, pics puis intégrales. Aucun changement
  silencieux de valeurs ou d'axe.
- Vue tactile NOx pour quelques actions; composant NMRium embarqué si licences,
  poids du bundle et API le permettent. Aucun import CDN à l'exécution.
- Sauvegarde locale des originaux et recette; lien explicite à l'expérience NOx.
- Dessin/molécules par format SMILES/Molfile indépendant; ne pas dépendre de
  l'API MolView sans identifiant client et droits d'intégration.

L'installation locale des bibliothèques est techniquement distincte de la
validation hors ligne dans un navigateur. Aucun build NMRium ni test navigateur
ou téléphone n'a été réalisé dans ce lot. Pas de cache PWA ajouté aux données
scientifiques ou à l'API authentifiée.

## Prochain critère de sortie

Un ZIP Bruker ¹H réel doit s'ouvrir **sans réseau** sur le téléphone Android cible,
produire un axe cohérent et un spectre comparable à TopSpin, permettre PH0/PH1,
ligne de base, référence et intégrale, puis réouvrir le projet sans perte. Les
tolérances doivent être définies sur ce jeu de référence avant validation.
Tester ZIP incomplet, archive trop grosse, ordre d'octets, `GRPDLY`/filtre
numérique, données déjà FT et annulation/reprise. Le FID 2D reste hors périmètre.

## Sources primaires

- NMRium composant et licence : https://github.com/cheminfo/nmrium ; https://www.npmjs.com/package/nmrium ; https://github.com/cheminfo/nmrium/blob/main/LICENSE .
- Parseur testé : https://github.com/cheminfo/nmr-parser ; https://github.com/cheminfo/nmr-parser/blob/main/src/fromBruker.js .
- Données test et licence : https://github.com/cheminfo/bruker-data-test .
- Formats/autotraitement documentés : https://docs.nmrium.org/20_1d-spectra/loading_a_spectrum/ .
- Traitements : https://docs.nmrium.org/help/processing/ .
- Licences des moteurs actuels : https://www.npmjs.com/package/brukerconverter ; https://www.npmjs.com/package/nmr-processing .
- MolView API et conditions d'intégration : https://molview.com/api/ .
