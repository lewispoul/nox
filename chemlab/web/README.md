# Interface NOx locale

Coquille Web mobile/PC en HTML/CSS/JavaScript, servie sur `/ui/` par le pilote Python. Aucun CDN, script tiers, service worker, stockage navigateur ou appel de modèle. Le jeton Bearer et les notes en cours restent seulement en mémoire; fermer/recharger la page les perd. Les notes non envoyées sont conservées séparément par expérience pendant cette page; elles ne suivent pas silencieusement un changement d’expérience. L’avertissement de fermeture dépend du navigateur et n’est pas une sauvegarde.

Fonctions : connexion locale, création/sélection de projets et expériences, note en brouillon local, journal filtré par expérience, liens vers GasCalc et RMN. Les résultats des modules ne sont pas encore rattachés automatiquement à une expérience. Le serveur conserve ses limites mono-utilisateur/boucle locale : une interface responsive n’autorise pas à exposer ce service sur le réseau du laboratoire.

Une note non confirmée conserve son identifiant et son contenu pour le réessai, sans autoriser un changement d’expérience ou une modification du contenu en attente. Un double appui pendant l’envoi ne lance pas de deuxième requête. Après une coupure, le même événement est renvoyé : le serveur déduplique. Une confirmation est acceptée seulement si identifiant, expérience, contenu et statut `draft_local` correspondent. Il n’existe aucune affirmation d’écriture dans FindMolecule. Les mesures affichées comme simulées ne sont pas des mesures de matériel réel.

Les données sont affichées par `textContent`; aucun HTML utilisateur n’est interprété. Les requêtes API utilisent `cache: no-store` et aucune authentification par cookie. Le backend doit aussi fixer ses en-têtes de non-cache pour les réponses protégées.

Les réponses asynchrones portent un contexte de session et de sélection. Une ancienne liste de projets ne peut pas rétablir un projet antérieur; tout changement de projet invalide la sélection d’expérience et les anciennes requêtes de journal. Une déconnexion pendant une note ne supprime pas le brouillon non confirmé, même si le serveur a déjà enregistré la requête; reconnecter puis réessayer le même événement.

Validation automatisée : `node tests/chemlab/ui/app.test.cjs` et `node tests/chemlab/ui/races.test.cjs`; syntaxe `node --check chemlab/web/app.js`. Ces tests couvrent surtout le réessai de note, les réponses de projets en ordre inversé, les changements de session, la déconnexion pendant un envoi et le câblage statique. Ils ne prouvent pas l’ergonomie tactile ni l’utilisation sur un téléphone réel.
