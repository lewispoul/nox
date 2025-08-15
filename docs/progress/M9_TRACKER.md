# M9 — Jobs Core + DB — Delivery Tracker

> Objectif : livrer le noyau des jobs IAM sur Nox (modèle + endpoints + worker minimal + métriques).
> Sortie attendue : API `/jobs` et `/modules` opérationnelles, DB migrée, worker “hello‑job” fonctionnel, métriques Prometheus exposées.

---

## ✅ Scope & livrables

- [ ] **DB migrations** : tables `jobs`, `modules` (+ index), JSONB pour `inputs/outputs`.
- [ ] **Endpoints Jobs** : `POST /jobs`, `GET /jobs/{id}`, `GET /jobs`, `POST /jobs/{id}/cancel`.
- [ ] **Endpoints Modules** : `GET /modules` (registry minimal, au moins 1 module “xtb_hello”).
- [ ] **Worker minimal** : conteneur qui lit `inputs`, écrit un fichier résultat, renvoie `succeeded`.
- [ ] **Métriques Prometheus** :
  - `nox_job_submitted_total{module,user_id}`
  - `nox_job_running{module}`
  - `nox_job_duration_seconds_bucket`
  - `nox_job_failures_total{module}`
- [ ] **RBAC/Quotas** : soumission requiert `role=user`; check quotas au `POST /jobs`.
- [ ] **SUMMARY** Copilot : ajouté à `PHASE2_PHASE3_PROGRESS.md` (section M9).

---

## 🗄️ Modèle de données (extraits)

**jobs** (colonnes clés)  
- `id UUID PK`, `user_id UUID`, `module TEXT`, `status TEXT` (`queued|running|succeeded|failed|canceled`)  
- `inputs JSONB`, `outputs JSONB`, `requested_resources JSONB`, `reserved_resources JSONB`  
- `created_at`, `started_at`, `ended_at`

**modules**  
- `name TEXT PK`, `version TEXT`, `caps JSONB`, `schema JSONB`, `enabled BOOL`

---

## 🧪 Tests d’acceptation (rapides)

### 1) API up & migrations ok
```bash
curl -fsS http://127.0.0.1:8081/health | jq .
```
- attendu: `"status": "ok"` + section jobs (optionnelle)

### 2) Registry modules
```bash
curl -fsS http://127.0.0.1:8081/modules | jq .
```
- attendu: contient `xtb_hello` (ou équivalent), `enabled: true`

### 3) Soumission d’un job
```bash
TOKEN="Bearer <JWT>"
curl -fsS -H "Authorization: $TOKEN" -H "Content-Type: application/json"   -d '{
        "module":"xtb_hello",
        "inputs":{"text":"hello from M9"},
        "requested_resources":{"cpu":1,"mem_mb":256,"wall_time_s":60}
      }'   http://127.0.0.1:8081/jobs | jq .
```
- attendu: `202 Accepted`, renvoie `{"job_id":"..."}`

### 4) Suivi du job
```bash
JOB_ID="..."
curl -fsS -H "Authorization: $TOKEN" http://127.0.0.1:8081/jobs/$JOB_ID | jq .
```
- attendu: statut passe `queued → running → succeeded`, `outputs.files` contient au moins 1 fichier

### 5) Liste des jobs
```bash
curl -fsS -H "Authorization: $TOKEN" "http://127.0.0.1:8081/jobs?status=succeeded&module=xtb_hello" | jq .
```
- attendu: liste non vide

### 6) Cancel (option)
```bash
curl -fsS -X POST -H "Authorization: $TOKEN" http://127.0.0.1:8081/jobs/$JOB_ID/cancel | jq .
```
- attendu: `canceled` si job en cours

---

## 📊 Vérifs Prometheus / Grafana

- `/metrics` expose :
  - `nox_job_submitted_total{module,user_id}`
  - `nox_job_running{module}`
  - `nox_job_duration_seconds_*`
  - `nox_job_failures_total{module}`

**Panels de base à créer :**
- *Jobs submitted (rate)* : `sum by(module) (rate(nox_job_submitted_total[5m]))`
- *Running jobs* : `sum by(module) (nox_job_running)`
- *Job duration (hist)* : `histogram_quantile(0.95, sum(rate(nox_job_duration_seconds_bucket[5m])) by (le, module))`

---

## 🔐 RBAC & Quotas (checks minimum)

- [ ] `POST /jobs` refuse si non authentifié (401) ou rôle insuffisant (403).
- [ ] `POST /jobs` calcule une “pré‑consommation” et refuse si quota insuffisant (429 ou 403).
- [ ] Violation loggée dans `quota_violations` + compteur `nox_quota_violations_total`.

---

## 🐛 Logs & pièges courants

- Erreurs 500 sur `/jobs` → vérifier JSONB null / schéma inputs non validé.
- Import Uvicorn/entrypoint → s’assurer que le module lancé est correct (`nox_api_src.api.nox_api:app`).
- Worker ne trouve pas la sandbox → vérifier chemins `sandbox://{user_id}/{job_id}` → mapping volume.
- JWT absent côté worker → si le worker appelle l’API (pull/push), utiliser un **service token**.

---

## 🚦 Go / No-Go (acceptation M9)

- [ ] Job “xtb_hello” soumis et terminé `succeeded` avec fichier de sortie.
- [ ] Endpoints `/jobs`, `/jobs/{id}`, `/jobs (list)`, `/modules` fonctionnels (200/202).
- [ ] Métriques `nox_job_*` visibles dans `/metrics` et dans Grafana.
- [ ] RBAC et quotas vérifiés a minima à la soumission.
- [ ] **Copilot SUMMARY** ajouté dans `PHASE2_PHASE3_PROGRESS.md` (section M9).

---

## 📝 Gabarit SUMMARY (à coller par Copilot)

```
# M9 — SUMMARY
- DB: migrations appliquées (jobs/modules)
- API: endpoints /jobs (POST, GET by id, list), /modules
- Worker: xtb_hello (écrit outputs + metrics)
- Metrics: nox_job_submitted_total, nox_job_running, nox_job_duration_seconds, nox_job_failures_total
- Tests: curl OK (submit, poll, list); Grafana panels créés
- RBAC/Quotas: check minimal à la soumission
- Risks/Debt: ...
- Next: M10 — adapter un module IAM réel (XTB/ML)
```

---

## 📎 Annexes

### Ex. réponse `GET /jobs/{id}`
```json
{
  "id": "f3d2e1c0-....",
  "module": "xtb_hello",
  "user_id": "cafe-babe-....",
  "status": "succeeded",
  "inputs": {"text": "hello from M9"},
  "outputs": {
    "files": ["sandbox://cafe-babe.../f3d2e1.../result.txt"],
    "metrics": {"duration_s": 0.53}
  },
  "requested_resources": {"cpu":1,"mem_mb":256,"wall_time_s":60},
  "created_at": "...",
  "started_at": "...",
  "ended_at": "..."
}
```
