# scripts/nox_audit.py
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------- Configurations ----------
EXCLUDED_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".parcel-cache",
    ".cache",
    ".git",
    ".gitlab",
    ".idea",
    ".vscode",
    ".github",
}

EXCLUDED_EXTS = {
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
    ".ico",
}

HASHABLE_EXTS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".sql",
    ".md",
    ".rst",
    ".html",
    ".css",
    ".scss",
    ".less",
    ".cfg",
    ".env",
    ".mjs",
    ".txt",
}

TARGET_DIRNAME = "nox-api-src"


# ---------- Data structures ----------
@dataclass
class FileMeta:
    path: str
    size: int
    ext: str
    mtime: str
    sha256: Optional[str] = None


@dataclass
class FolderStats:
    path: str
    file_count: int = 0  # total in subtree
    total_size: int = 0  # total in subtree
    direct_files: int = 0  # immediate files only


# ---------- Utilities ----------
def fail(msg: str, code: int = 1) -> None:
    print(f"[nox_audit] ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def ok(msg: str) -> None:
    print(f"[nox_audit] {msg}")


def local_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def sha256_file(path: Path, bufsize: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(bufsize)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def is_hashable(path: Path) -> bool:
    ext = path.suffix.lower()
    if ext in HASHABLE_EXTS:
        return True
    # Special case for .env* files without extension
    name = path.name
    if name.startswith(".env"):
        return True
    return False


def should_exclude_file(path: Path) -> bool:
    return path.suffix.lower() in EXCLUDED_EXTS


def should_skip_dir(dirname: str) -> bool:
    return dirname in EXCLUDED_DIRS


def find_nox_api_src(repo_root: Path) -> Path:
    # Prefer exactly repo_root / nox-api-src
    candidate = repo_root / TARGET_DIRNAME
    if candidate.is_dir():
        return candidate
    # Otherwise, search the tree and pick the shallowest match
    matches = [p for p in repo_root.rglob(TARGET_DIRNAME) if p.is_dir()]
    if not matches:
        fail(f"Répertoire '{TARGET_DIRNAME}' introuvable sous {repo_root.resolve()}")
    matches.sort(key=lambda p: len(p.relative_to(repo_root).parts))
    return matches[0]


# ---------- Scanning ----------
def scan_directory(root: Path) -> Tuple[List[FileMeta], Dict[str, FolderStats], int]:
    files: List[FileMeta] = []
    folders: Dict[str, FolderStats] = {}
    ignored_files_count = 0

    folders["."] = FolderStats(path=".")

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter excluded directories in-place
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]

        rel_dir = Path(dirpath).relative_to(root)
        rel_dir_str = "." if str(rel_dir) == "." else str(rel_dir).replace("\\", "/")
        if rel_dir_str not in folders:
            folders[rel_dir_str] = FolderStats(path=rel_dir_str)

        for name in filenames:
            abs_path = Path(dirpath) / name
            try:
                st = abs_path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            if should_exclude_file(abs_path):
                ignored_files_count += 1
                continue

            rel_path = abs_path.relative_to(root)
            rel_path_str = str(rel_path).replace("\\", "/")
            ext = abs_path.suffix.lower()
            size = st.st_size
            mtime = local_iso(st.st_mtime)

            fm = FileMeta(
                path=rel_path_str,
                size=size,
                ext=ext if ext else "",
                mtime=mtime,
                sha256=None,
            )
            if is_hashable(abs_path):
                try:
                    fm.sha256 = sha256_file(abs_path)
                except Exception:
                    fm.sha256 = None

            files.append(fm)

            # Update folder stats upward
            folders[rel_dir_str].direct_files += 1
            parts = Path(rel_path).parts[:-1]
            for depth in range(len(parts) + 1):
                key = "." if depth == 0 else "/".join(parts[:depth])
                if key not in folders:
                    folders[key] = FolderStats(path=key)
                folders[key].file_count += 1
                folders[key].total_size += size

    return files, folders, ignored_files_count


# ---------- Tree rendering ----------
def build_tree(files: List[FileMeta]) -> Dict:
    root = {"name": ".", "children": {}, "_files": []}
    for fm in files:
        parts = Path(fm.path).parts
        node = root
        for d in parts[:-1]:
            node = node["children"].setdefault(
                d, {"name": d, "children": {}, "_files": []}
            )
        node["_files"].append(fm)
    return root


def render_tree(
    node: Dict,
    folders: Dict[str, FolderStats],
    depth: int,
    max_depth: int,
    prefix: str = "",
) -> List[str]:
    lines: List[str] = []
    items = sorted(node["children"].items(), key=lambda kv: kv[0].lower())
    last_idx = len(items) - 1
    for idx, (name, child) in enumerate(items):
        child_rel_path = f"{prefix}{name}".strip("/")
        stats_key = "." if child_rel_path == "" else child_rel_path
        fs = folders.get(stats_key, FolderStats(path=stats_key))
        label = f"{name}/  [files:{fs.direct_files} total:{fs.file_count} size:{fs.total_size}]"
        branch = "└──" if idx == last_idx else "├──"
        lines.append(f"{'  ' * depth}{branch} {label}")
        if depth + 1 < max_depth:
            new_prefix = f"{child_rel_path}/" if child_rel_path else ""
            lines.extend(render_tree(child, folders, depth + 1, max_depth, new_prefix))
    return lines


# ---------- Duplicates ----------
def group_duplicates_by_name(files: List[FileMeta]) -> List[List[FileMeta]]:
    buckets: Dict[str, List[FileMeta]] = {}
    for f in files:
        key = Path(f.path).name.lower()
        buckets.setdefault(key, []).append(f)
    return [v for v in buckets.values() if len(v) > 1]


def group_duplicates_by_hash(files: List[FileMeta]) -> List[List[FileMeta]]:
    buckets: Dict[str, List[FileMeta]] = {}
    for f in files:
        if f.sha256:
            buckets.setdefault(f.sha256, []).append(f)
    return [v for v in buckets.values() if len(v) > 1]


def pick_reference(candidates: List[FileMeta]) -> FileMeta:
    def score(f: FileMeta) -> Tuple[int, float]:
        in_api = 1 if f.path.startswith("api/") else 0
        try:
            ts = datetime.fromisoformat(f.mtime).timestamp()
        except Exception:
            ts = 0.0
        return (in_api, ts)

    return sorted(candidates, key=score, reverse=True)[0]


# ---------- Markdown rendering ----------
def human_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    f = float(n)
    while f >= 1024 and i < len(units) - 1:
        f /= 1024.0
        i += 1
    if i == 0:
        return f"{int(f)} {units[i]}"
    return f"{f:.2f} {units[i]}"


def render_markdown(
    root_label: str,
    files: List[FileMeta],
    folders: Dict[str, FolderStats],
    ignored_count: int,
    depth: int,
    max_top: int,
) -> str:
    now = datetime.now().isoformat(timespec="seconds")
    total_files = len(files)
    total_folders = len([k for k in folders.keys() if k != "."])
    total_size = sum(f.size for f in files)

    tree_root = build_tree(files)
    tree_lines = render_tree(tree_root, folders, 0, depth)
    tree_text = (
        "```\n" + "\n".join(tree_lines) + "\n```"
        if tree_lines
        else "_Aucun sous-dossier visible à cette profondeur._"
    )

    top_files = sorted(files, key=lambda f: f.size, reverse=True)[:max_top]
    dup_name_groups = group_duplicates_by_name(files)
    dup_hash_groups = group_duplicates_by_hash(files)

    groups: Dict[str, List[FileMeta]] = {}
    for f in files:
        parts = Path(f.path).parts
        top = parts[0] if len(parts) > 1 else "."
        groups.setdefault(top, []).append(f)

    json_payload = {
        "summary": {
            "generated_at": now,
            "root": root_label,
            "files": total_files,
            "folders": total_folders,
            "ignored_files": ignored_count,
            "total_size": total_size,
        },
        "folders": {k: asdict(v) for k, v in folders.items()},
        "files": [asdict(f) for f in files],
        "duplicates_by_name": [[asdict(x) for x in grp] for grp in dup_name_groups],
        "duplicates_by_hash": [[asdict(x) for x in grp] for grp in dup_hash_groups],
    }
    json_block = (
        "```json\n"
        + json.dumps(json_payload, ensure_ascii=False, separators=(",", ":"))
        + "\n```"
    )

    md = []
    md.append("# Audit nox-api-src")
    md.append("")
    md.append(f"**Date**: {now}  ")
    md.append("**Racine analysée**: `nox-api-src/`  ")
    md.append("")
    md.append("## Résumé")
    md.append("")
    md.append(f"- Dossiers: {total_folders}")
    md.append(f"- Fichiers: {total_files}")
    md.append(f"- Taille totale: {human_size(total_size)}")
    md.append(f"- Fichiers ignorés: {ignored_count}")
    if dup_name_groups:
        md.append(f"- Doublons par nom détectés: {len(dup_name_groups)} groupes")
    if dup_hash_groups:
        md.append(f"- Doublons par contenu détectés: {len(dup_hash_groups)} groupes")

    md.append("")
    md.append("## Arborescence (profondeur limitée)")
    md.append("")
    md.append(tree_text)

    md.append("")
    md.append("## Top fichiers par taille")
    md.append("")
    if top_files:
        md.append("| Path | Size | MTime |")
        md.append("| --- | ---: | --- |")
        for f in top_files:
            md.append(f"| `{f.path}` | {human_size(f.size)} | {f.mtime} |")
    else:
        md.append("_Aucun fichier._")

    md.append("")
    md.append("## Inventaire des fichiers par dossier top-level")
    md.append("")
    for top, lst in sorted(groups.items(), key=lambda kv: kv[0].lower()):
        md.append(f"### `{top}`")
        md.append("")
        md.append("| Path | Size | Ext | MTime | SHA256 |")
        md.append("| --- | ---: | --- | --- | --- |")
        for f in sorted(lst, key=lambda x: x.path.lower()):
            md.append(
                f"| `{f.path}` | {f.size} | `{f.ext}` | {f.mtime} | `{f.sha256 or ''}` |"
            )
        md.append("")

    md.append("## Doublons par nom")
    md.append("")
    if dup_name_groups:
        for grp in dup_name_groups:
            ref = pick_reference(grp)
            md.append(f"- Référence suggérée: `{ref.path}`")
            for f in sorted(grp, key=lambda x: x.path.lower()):
                mark = " (ref)" if f.path == ref.path else ""
                md.append(f"  - `{f.path}` | {f.size} B | {f.mtime}{mark}")
    else:
        md.append("_Aucun doublon par nom._")

    md.append("")
    md.append("## Doublons par contenu (hash)")
    md.append("")
    if dup_hash_groups:
        for grp in dup_hash_groups:
            ref = pick_reference(grp)
            sha = grp[0].sha256
            md.append(f"- SHA256: `{sha}`  ")
            md.append(f"  Référence suggérée: `{ref.path}`")
            for f in sorted(grp, key=lambda x: x.path.lower()):
                mark = " (ref)" if f.path == ref.path else ""
                md.append(f"  - `{f.path}` | {f.size} B | {f.mtime}{mark}")
    else:
        md.append("_Aucun doublon par hash._")

    md.append("")
    md.append("## Redondances de structure et configs")
    md.append("")
    md.append(
        "- Vérifier la présence de dossiers proches comme `api`, `api-old`, `api_backup`, `archive`."
    )
    md.append(
        "- Vérifier la duplication potentielle de modules entre `ai/`, `api/`, `scripts/`."
    )
    md.append(
        "- Vérifier les configs multiples et chevauchantes: `pyproject.toml`, `setup.cfg`, `ruff.toml`, `.flake8`, `tsconfig.json`, `package.json`."
    )

    md.append("")
    md.append("## Recommandations de nettoyage (non destructif)")
    md.append("")
    md.append("1. Geler l'état actuel dans une branche ou un tag.")
    md.append(
        "2. Écrire des tests rapides pour valider imports et endpoints critiques."
    )
    md.append(
        "3. Consolider les duplications par nom ou par hash en gardant la référence la plus récente située dans `api/` si pertinent."
    )
    md.append(
        "4. Déplacer artefacts, logs et caches vers `artifacts/` ou les ignorer via VCS."
    )
    md.append(
        "5. Unifier les configurations redondantes et centraliser les scripts dans `scripts/`."
    )
    md.append("")
    md.append("Arborescence cible suggérée:")
    md.append("```")
    md.append("nox-api-src/")
    md.append("  api/")
    md.append("  ai/")
    md.append("  scripts/")
    md.append("  tests/")
    md.append("  docs/")
    md.append("  configs/")
    md.append("```")

    md.append("")
    md.append("## Annexe A. Heuristiques")
    md.append("")
    md.append("- Exclusions dossiers: " + ", ".join(sorted(EXCLUDED_DIRS)))
    md.append("- Exclusions extensions: " + ", ".join(sorted(EXCLUDED_EXTS)))
    md.append("- Extensions hashées: " + ", ".join(sorted(HASHABLE_EXTS)))
    md.append("- Taille dossier = somme des tailles des fichiers du sous-arbre.")
    md.append(
        "- Doublons par nom: groupement insensible à la casse sur le nom de fichier."
    )
    md.append("- Doublons par hash: groupement sur SHA256 des fichiers texte/code.")

    md.append("")
    md.append("## Annexe B. JSON machine lisible")
    md.append("")
    md.append(json_block)

    md.append("")
    md.append("## Checklist de validation")
    md.append("")
    md.append("- [ ] Tous les chemins listés existent dans `nox-api-src/`.")
    md.append("- [ ] Recalculer 3 SHA256 au hasard et comparer avec le tableau.")
    md.append(
        "- [ ] Les recommandations n'impliquent pas de suppression sans sauvegarde."
    )
    md.append("- [ ] Les dossiers exclus n'apparaissent pas dans l'inventaire.")
    md.append(
        "- [ ] Les imports et endpoints critiques passent les tests après consolidation."
    )
    md.append(
        "- [ ] Les chemins relatifs restent valides après tout mouvement suggéré."
    )

    return "\n".join(md)


# ---------- Main ----------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit nox-api-src et écrire un rapport Markdown."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Chemin explicite vers nox-api-src (doit être le dossier lui-même).",
    )
    parser.add_argument(
        "--depth", type=int, default=6, help="Profondeur max de l'arbre."
    )
    parser.add_argument(
        "--max-top", type=int, default=50, help="Top N plus gros fichiers."
    )
    parser.add_argument(
        "--no-hash",
        action="store_true",
        help="Désactivé (compat rétro) — les hash sont déjà conditionnés par extensions.",
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default=None,
        help="Chemin vers le dossier reports existant (par défaut: <repo_root>/reports).",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()

    # Résoudre le chemin de nox-api-src
    if args.root:
        target = Path(args.root).resolve()
        if not target.is_dir() or target.name != TARGET_DIRNAME:
            fail(
                f"--root doit pointer vers le dossier '{TARGET_DIRNAME}' lui-même: {target}"
            )
    else:
        target = find_nox_api_src(repo_root)

    ok(f"Racine d'analyse: {target}")

    # Résoudre le dossier reports (ne jamais créer)
    reports_dir = (
        Path(args.reports_dir).resolve()
        if args.reports_dir
        else (repo_root / "reports")
    )
    if not reports_dir.is_dir():
        fail(
            f"Le dossier reports n'existe pas: {reports_dir}. Crée-le manuellement pour éviter les doublons."
        )
    report_path = reports_dir / "nox_api_src_audit.md"

    ok("Scan des fichiers…")
    files, folders, ignored = scan_directory(target)

    ok("Génération du rapport…")
    md = render_markdown(
        "nox-api-src", files, folders, ignored, depth=args.depth, max_top=args.max_top
    )

    ok(f"Écriture: {report_path}")
    report_path.write_text(md, encoding="utf-8")

    # Résumé console
    total_size = sum(f.size for f in files)
    ok(
        f"Terminé. Fichiers: {len(files)}, Dossiers: {len([k for k in folders if k != '.'])}, "
        f"Ignorés: {ignored}, Taille: {total_size} B"
    )


if __name__ == "__main__":
    main()
