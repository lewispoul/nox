Plan de Création de l’Assistant DevOps

1. Objectif

Mettre en place un agent automatisé capable de :

Communiquer via l’API OpenAI (ChatGPT) avec un contexte projet issu de copilot-plan.md et du repo Git.

Utiliser la sandbox Nox pour exécuter, tester et déployer du code.

Effectuer des modifications dans le repo Git de manière sécurisée.

Arrêter l’exécution et produire un rapport complet en cas de problème complexe.

2. Architecture

Toi ↔ ChatGPT (planification) ↔ Assistant DevOps ↔ Nox API ↔ Sandbox
                                       ↕
                                     Repo Git (mémoire)

3. Étapes de Mise en Place

Étape 1 – Client Python de Base

Créer un script Python (assistant_devops.py) qui :

Charge les variables d’environnement (token OpenAI, URL Nox API, token API Nox).

Établit la connexion à l’API OpenAI.

Permet d’envoyer et recevoir des messages.

Étape 2 – Gestion du Contexte

Charger le contenu de copilot-plan.md pour donner la vision complète du projet.

Extraire les logs récents et l’état du repo (branche, commits récents).

Stocker le contexte dans la session pour que chaque requête OpenAI parte avec ces infos.

Étape 3 – Connexion au Repo Git

Configurer l’accès SSH ou HTTPS avec jeton personnel.

Implémenter des commandes git pull, git commit -am et git push après validation.

S’assurer que chaque commit est lié à une tâche ou étape du plan.

Étape 4 – Intégration Nox API

Ajout de fonctions Python pour :

Upload de fichiers vers la sandbox (/put).

Exécution de scripts Python (/run_py).

Exécution de commandes shell sécurisées (/run_sh).

Vérification de l’état (/health).

Gestion des timeouts et interdiction de certaines commandes.

Étape 5 – Pipeline de Tests Automatisés

Scripts de validation pour :

systemctl status nox-api actif.

/health renvoie OK.

Upload + exécution de script Python.

Vérification des restrictions /run_sh.

Étape 6 – Règles d’Arrêt et Sécurité

Si erreur critique détectée (logs, exceptions, test échoué) :

Stopper l’exécution.

Générer un rapport complet :

Logs système

Code ou fichiers impliqués

Contexte du problème

Attendre instruction manuelle avant de continuer.

Étape 7 – Boucle de Collaboration

L’Assistant DevOps travaille en continu :

Reçoit instructions depuis ChatGPT.

Exécute, teste, commit, push.

Rend compte avec rapports détaillés.

Communication bidirectionnelle entre ChatGPT et l’Assistant via un canal API ou WebSocket.

4. Livrables

assistant_devops.py (client principal)

config.env (variables d’environnement)

Scripts de test (test_nox_api.sh, test_sandbox.sh)

Documentation (README.md)

5. Prochaines Actions

Créer squelette assistant_devops.py avec connexion OpenAI + Nox API.

Intégrer chargement du contexte (copilot-plan.md + logs Git).

Tester connexion bidirectionnelle ChatGPT ↔ Assistant DevOps.

