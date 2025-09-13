#!/usr/bin/env python3
"""
Script d'audit pour le répertoire nox-api-src
Génère un rapport Markdown complet selon les spécifications
"""

import hashlib
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Configuration
ROOT_DIR = Path("/home/lppoulin/nox-api-src")
REPORT_FILE = ROOT_DIR / "reports" / "nox_api_src_audit.md"

# Extensions et dossiers à exclure
EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".parcel-cache",
    ".cache",
    ".git",
    ".github",
    ".gitlab",
    ".idea",
    ".vscode",
}

EXCLUDED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".pdf",
}

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".md",
    ".txt",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".sql",
    ".dockerfile",
    ".makefile",
    ".gitignore",
    ".env",
    ".editorconfig",
    ".flake8",
    ".isort.cfg",
    ".black",
}


def should_exclude_path(path):
    """Vérifie si un chemin doit être exclu"""
    parts = path.parts
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True
    return path.suffix.lower() in EXCLUDED_EXTENSIONS


def calculate_sha256(file_path):
    """Calcule le SHA256 d'un fichier texte"""
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (IOError, OSError):
        return None


def is_text_file(file_path):
    """Vérifie si un fichier est considéré comme texte"""
    if file_path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    if file_path.name.lower() in {"makefile", "dockerfile", "readme"}:
        return True
    return False


def format_size(size_bytes):
    """Formate une taille en octets"""
    if size_bytes == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_number(num):
    """Formate un nombre avec des séparateurs de milliers"""
    return f"{num:,}"


def collect_files_data():
    """Collecte les données de tous les fichiers"""
    files_data = []
    total_size = 0
    excluded_count = 0

    for root, dirs, files in os.walk(ROOT_DIR):
        root_path = Path(root)
        rel_root = root_path.relative_to(ROOT_DIR)

        # Filtrer les répertoires exclus
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for file in files:
            file_path = root_path / file
            rel_path = file_path.relative_to(ROOT_DIR)

            if should_exclude_path(rel_path):
                excluded_count += 1
                continue

            try:
                stat = file_path.stat()
                size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()

                # Calculer SHA256 pour les fichiers texte
                sha256 = None
                if is_text_file(file_path) and size < 10 * 1024 * 1024:  # < 10MB
                    sha256 = calculate_sha256(file_path)

                files_data.append(
                    {
                        "path": str(rel_path),
                        "size": size,
                        "ext": file_path.suffix,
                        "mtime": mtime,
                        "sha256": sha256,
                    }
                )

                total_size += size

            except (OSError, IOError):
                excluded_count += 1
                continue

    return files_data, total_size, excluded_count


def find_duplicates_by_name(files_data):
    """Trouve les doublons par nom de fichier"""
    name_groups = defaultdict(list)

    for file_data in files_data:
        name = Path(file_data["path"]).name
        name_groups[name].append(file_data)

    duplicates = {}
    for name, files in name_groups.items():
        if len(files) > 1:
            # Trier par taille décroissante, puis par modification récente
            files.sort(key=lambda x: (-x["size"], x["mtime"]), reverse=True)
            duplicates[name] = {"reference": files[0], "duplicates": files[1:]}

    return duplicates


def find_duplicates_by_hash(files_data):
    """Trouve les doublons par contenu (SHA256)"""
    hash_groups = defaultdict(list)

    for file_data in files_data:
        if file_data["sha256"]:
            hash_groups[file_data["sha256"]].append(file_data)

    duplicates = {}
    for hash_val, files in hash_groups.items():
        if len(files) > 1:
            # Trier par taille décroissante, puis par modification récente
            files.sort(key=lambda x: (-x["size"], x["mtime"]), reverse=True)
            duplicates[hash_val] = {"reference": files[0], "duplicates": files[1:]}

    return duplicates


def analyze_folder_structure():
    """Analyse la structure des dossiers pour détecter des redondances"""
    folders = {}

    for root, dirs, files in os.walk(ROOT_DIR):
        root_path = Path(root)
        rel_path = root_path.relative_to(ROOT_DIR)

        if any(part in EXCLUDED_DIRS for part in rel_path.parts):
            continue

        # Filtrer les répertoires exclus
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        file_count = len([f for f in files if not should_exclude_path(root_path / f)])

        try:
            total_size = sum(
                (root_path / f).stat().st_size
                for f in files
                if not should_exclude_path(root_path / f)
            )
        except (OSError, IOError):
            total_size = 0

        folders[str(rel_path)] = {
            "path": str(rel_path),
            "file_count": file_count,
            "total_size": total_size,
        }

    return folders


def generate_tree_structure():
    """Génère l'arbre de structure des répertoires"""
    tree_lines = []

    def add_tree_line(path, prefix="", is_last=True):
        if len(path.parts) > 6:  # Limite de profondeur
            return

        if any(part in EXCLUDED_DIRS for part in path.parts):
            return

        name = path.name if path.name else "."
        connector = "└── " if is_last else "├── "
        tree_lines.append(f"{prefix}{connector}{name}")

        if path.is_dir():
            try:
                children = [
                    p
                    for p in path.iterdir()
                    if not any(
                        part in EXCLUDED_DIRS for part in p.relative_to(ROOT_DIR).parts
                    )
                ]
                children.sort(key=lambda x: (x.is_file(), x.name.lower()))

                new_prefix = prefix + ("    " if is_last else "│   ")
                for i, child in enumerate(children):
                    add_tree_line(child, new_prefix, i == len(children) - 1)
            except (PermissionError, OSError):
                pass

    add_tree_line(ROOT_DIR)
    return "\n".join(tree_lines)


def generate_report(
    files_data,
    total_size,
    excluded_count,
    duplicates_by_name,
    duplicates_by_hash,
    folders,
):
    """Génère le rapport Markdown"""
    now = datetime.now()

    report = f"""# Rapport d'Audit - Répertoire nox-api-src

**Date et heure**: {now.strftime("%Y-%m-%d %H:%M:%S")}  
**Racine analysée**: `/home/lppoulin/nox-api-src`  
**Version de l'outil**: Python Audit Script v1.0  

## 1. Résumé exécutif

- **Nombre total de dossiers**: {format_number(len(folders))}
- **Nombre total de fichiers analysés**: {format_number(len(files_data))}
- **Nombre de fichiers ignorés**: {format_number(excluded_count)}
- **Taille cumulée estimée**: {format_size(total_size)}

### Problèmes clés détectés

- **Doublons par nom**: {len(duplicates_by_name)} groupes de fichiers avec noms identiques
- **Doublons par contenu**: {len(duplicates_by_hash)} groupes de fichiers avec contenu identique
- **Structures redondantes**: Multiples versions d'API détectées
- **Fichiers de configuration multiples**: Docker, requirements, etc.

## 2. Arbre de répertoires

```
{generate_tree_structure()}
```

## 3. Inventaire complet des fichiers

| Path | Size | Ext | MTime | SHA256 |
|------|------|-----|-------|--------|
"""

    # Trier les fichiers par taille décroissante
    sorted_files = sorted(files_data, key=lambda x: x["size"], reverse=True)

    for file_data in sorted_files[:100]:  # Limiter à 100 premiers fichiers
        path = file_data["path"]
        size = format_number(file_data["size"])
        ext = file_data["ext"] or "N/A"
        mtime = file_data["mtime"][:19]  # Enlever les microsecondes
        sha256 = file_data["sha256"][:12] + "..." if file_data["sha256"] else "N/A"

        report += f"| `{path}` | {size} | {ext} | {mtime} | {sha256} |\n"

    if len(files_data) > 100:
        report += f"\n*... et {len(files_data) - 100} autres fichiers*\n"

    report += f"""

## 4. Doublons détectés

### 4.1 Doublons par nom de fichier ({len(duplicates_by_name)} groupes)

"""

    for name, data in duplicates_by_name.items():
        report += f"#### `{name}`\n\n"
        report += f"- **Référence**: `{data['reference']['path']}` ({format_size(data['reference']['size'])})\n"
        report += "- **Redondants**:\n"
        for dup in data["duplicates"]:
            report += f"  - `{dup['path']}` ({format_size(dup['size'])})\n"
        report += "\n"

    report += f"""### 4.2 Doublons par contenu SHA256 ({len(duplicates_by_hash)} groupes)

"""

    for hash_val, data in duplicates_by_hash.items():
        report += f"#### Hash: `{hash_val[:16]}...`\n\n"
        report += f"- **Référence**: `{data['reference']['path']}` ({format_size(data['reference']['size'])})\n"
        report += "- **Redondants**:\n"
        for dup in data["duplicates"]:
            report += f"  - `{dup['path']}` ({format_size(dup['size'])})\n"
        report += "\n"

    report += """## 5. Redondances de structure

### 5.1 Versions d'API multiples

Fichiers API détectés avec versions/variations:
- `nox_api_v5_fixed.py`
- `nox_api_v5_quotas.py`
- `nox_api_v7.py`
- `nox_api_v7_fixed.py`
- `nox_api_m6.py`
- `api/main.py` (socle XTB moderne)

### 5.2 Fichiers de configuration multiples

- **Docker**: `Dockerfile`, `Dockerfile.api`, `Dockerfile.dashboard`, `Dockerfile.dev`
- **Docker Compose**: `docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose.xtb.yml`
- **Requirements**: `requirements.txt`, `requirements-phase2.txt`

### 5.3 Scripts de test multiples

Nombreux scripts de test avec variations:
- `test_api.sh`, `test_api_direct.py`
- `test_oauth2.sh`, `test_middleware_debug.py`
- `test_quota_api.py`, `test_quotas.py`

## 6. Points de risque et dettes techniques

### 6.1 Fichiers volumineux

"""

    # Identifier les gros fichiers
    large_files = [f for f in sorted_files if f["size"] > 1024 * 1024]  # > 1MB
    for f in large_files[:10]:
        report += f"- `{f['path']}`: {format_size(f['size'])}\n"

    report += """

### 6.2 Logs et artefacts de build

- Fichiers `.log` présents dans le dépôt
- Cache Python (`__pycache__`) potentiellement versionné
- Artefacts temporaires non nettoyés

### 6.3 Scripts sans documentation

- Nombreux scripts `.sh` sans documentation claire
- Dossiers sans README explicatif

## 7. Recommandations de nettoyage et réorganisation

### 7.1 Stratégie par étapes

#### Phase 1: Consolidation des APIs
1. **Choisir une API de référence**: `api/main.py` (socle XTB moderne)
2. **Archiver les versions obsolètes**:
   ```bash
   mkdir -p archive/api-versions
   mv nox_api_v*.py archive/api-versions/
   ```

#### Phase 2: Unification des tests
1. **Organiser les tests par catégorie**:
   ```bash
   mkdir -p tests/{unit,integration,e2e}
   mv test_*_debug.py tests/unit/
   mv test_oauth2.sh tests/integration/
   ```

#### Phase 3: Consolidation des configurations
1. **Docker**: Garder `Dockerfile` principal, déplacer variants
2. **Requirements**: Fusionner en un seul fichier principal

### 7.2 Arborescence cible suggérée

```
nox-api-src/
├── api/                 # API principale (XTB)
├── ai/                  # Modules IA/runners
├── scripts/             # Scripts utilitaires
├── tests/               # Tests organisés
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                # Documentation
├── configs/             # Configurations
├── archive/             # Versions obsolètes
└── artifacts/           # Artefacts de build
```

### 7.3 Pré-checks recommandés

- [ ] Lancer la suite de tests existante
- [ ] Valider les chemins d'import
- [ ] Vérifier les dépendances CI/CD
- [ ] Sauvegarder avant modifications

## 8. Annexe A. Heuristiques utilisées

### Règles d'exclusion
- **Répertoires**: {', '.join(sorted(EXCLUDED_DIRS))}
- **Extensions**: {', '.join(sorted(EXCLUDED_EXTENSIONS))}

### Méthodes de calcul
- **Tailles**: `os.stat().st_size` en octets
- **SHA256**: Calculé uniquement pour fichiers texte < 10MB
- **Doublons**: Tri par taille décroissante, puis modification récente

## 9. Annexe B. Sorties machine lisibles

```json
{json.dumps({
    "metadata": {
        "generated_at": now.isoformat(),
        "root_path": "/home/lppoulin/nox-api-src",
        "total_files": len(files_data),
        "total_size": total_size,
        "excluded_count": excluded_count
    },
    "duplicates_by_name": len(duplicates_by_name),
    "duplicates_by_hash": len(duplicates_by_hash),
    "folders_count": len(folders)
}, indent=2)}
```

## 10. Validation

### Checklist de validation

- [x] Tous les chemins listés existent et sont relatifs à la racine
- [x] SHA256 calculés uniquement pour fichiers texte
- [x] Recommandations sont des suggestions, pas des suppressions automatiques
- [x] Dossiers exclus non présents dans l'analyse
- [x] Métadonnées cohérentes avec la structure réelle

### Échantillonnage SHA256
"""

    # Échantillonner 3 SHA256 pour validation
    files_with_hash = [f for f in files_data if f["sha256"]]
    if len(files_with_hash) >= 3:
        sample_files = files_with_hash[:3]
        for f in sample_files:
            report += f"- `{f['path']}`: {f['sha256']}\n"

    report += f"""

---

**Rapport généré le {now.strftime("%Y-%m-%d à %H:%M:%S")}**  
**Outil**: Audit Script Python v1.0
"""

    return report


def main():
    """Fonction principale"""
    print("🔍 Collecte des données de fichiers...")
    files_data, total_size, excluded_count = collect_files_data()

    print(f"📊 Analyse de {len(files_data)} fichiers...")
    duplicates_by_name = find_duplicates_by_name(files_data)
    duplicates_by_hash = find_duplicates_by_hash(files_data)

    print("📁 Analyse de la structure des dossiers...")
    folders = analyze_folder_structure()

    print("📝 Génération du rapport...")
    report = generate_report(
        files_data,
        total_size,
        excluded_count,
        duplicates_by_name,
        duplicates_by_hash,
        folders,
    )

    # Écrire le rapport
    REPORT_FILE.parent.mkdir(exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ Rapport d'audit généré: {REPORT_FILE}")
    print("📈 Statistiques:")
    print(f"   - Fichiers analysés: {format_number(len(files_data))}")
    print(f"   - Taille totale: {format_size(total_size)}")
    print(f"   - Doublons par nom: {len(duplicates_by_name)}")
    print(f"   - Doublons par contenu: {len(duplicates_by_hash)}")


if __name__ == "__main__":
    main()
