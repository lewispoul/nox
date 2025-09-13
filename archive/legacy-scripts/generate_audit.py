#!/usr/bin/env python3
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Configuration
ROOT_DIR = Path("/home/lppoulin/nox-api-src")
REPORT_FILE = ROOT_DIR / "reports" / "nox_api_src_audit.md"


def generate_quick_report():
    """Génère un rapport rapide"""
    now = datetime.now()

    # Collecte rapide des données
    files_data = []
    total_size = 0

    for root, dirs, files in os.walk(ROOT_DIR):
        # Exclure les dossiers cachés et temporaires
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and d not in ["__pycache__", "node_modules"]
        ]

        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(ROOT_DIR)

            # Ignorer les fichiers binaires et temporaires
            if file.startswith(".") or file.endswith((".pyc", ".png", ".jpg", ".pdf")):
                continue

            try:
                size = file_path.stat().st_size
                files_data.append(
                    {"path": str(rel_path), "size": size, "ext": file_path.suffix}
                )
                total_size += size
            except:
                continue

    # Générer le rapport
    report = f"""# Rapport d'Audit - Répertoire nox-api-src

**Date**: {now.strftime("%Y-%m-%d %H:%M:%S")}  
**Racine**: `/home/lppoulin/nox-api-src`  

## Résumé

- **Fichiers analysés**: {len(files_data)}
- **Taille totale**: {total_size:,} octets ({total_size/1024/1024:.1f} MB)

## Structure principale

```
nox-api-src/
├── api/                 # API XTB moderne
├── ai/                  # Runners et IA  
├── tests/               # Tests
├── reports/             # Rapports
├── docs/                # Documentation
├── scripts/             # Scripts utilitaires
└── [fichiers racine]   # Versions API multiples
```

## Top 20 fichiers par taille

"""

    # Trier par taille
    sorted_files = sorted(files_data, key=lambda x: x["size"], reverse=True)[:20]

    for f in sorted_files:
        size_mb = f["size"] / 1024 / 1024
        report += f"- `{f['path']}` - {size_mb:.2f} MB\n"

    report += """

## Doublons potentiels détectés

### Fichiers API multiples
- `nox_api_v5_fixed.py`
- `nox_api_v5_quotas.py` 
- `nox_api_v7.py`
- `nox_api_v7_fixed.py`
- `nox_api_m6.py`
- `api/main.py` (recommandé comme référence)

### Configurations Docker
- `Dockerfile`
- `Dockerfile.api`
- `Dockerfile.dashboard`
- `Dockerfile.dev`

### Docker Compose
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `docker-compose.xtb.yml`

## Recommandations

1. **Consolider les APIs** - Utiliser `api/main.py` comme référence
2. **Organiser les tests** - Regrouper dans `tests/`
3. **Archiver les versions obsolètes**
4. **Unifier les configurations Docker**

## Fichiers analysés par extension

"""

    # Compter par extension
    ext_count = defaultdict(int)
    for f in files_data:
        ext = f["ext"] if f["ext"] else "sans_extension"
        ext_count[ext] += 1

    for ext, count in sorted(ext_count.items(), key=lambda x: x[1], reverse=True):
        report += f"- `{ext}`: {count} fichiers\n"

    report += f"""

---
*Rapport généré le {now.strftime("%Y-%m-%d à %H:%M:%S")}*
"""

    return report


def main():
    print("Génération du rapport d'audit...")

    # S'assurer que le dossier reports existe
    REPORT_FILE.parent.mkdir(exist_ok=True)

    # Générer et écrire le rapport
    report = generate_quick_report()

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ Rapport créé: {REPORT_FILE}")
    print(f"📄 Taille: {len(report)} caractères")


if __name__ == "__main__":
    main()
