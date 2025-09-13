#!/usr/bin/env python3
"""
NOX Backup & Restore CLI
Lists available backups, allows creation of new backups, and restores from selected backup files.
"""
import shutil
from pathlib import Path

BACKUP_DIR = "/opt/nox/backups"
APP_DIR = "/opt/nox/app"
DB_BACKUP_EXT = ".sql"
APP_BACKUP_EXT = ".tar.gz"


def list_backups():
    backups = []
    for f in Path(BACKUP_DIR).glob("*"):
        backups.append(f)
    return sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)


def create_app_backup():
    backup_name = f"nox-app-backup-{int(time.time())}{APP_BACKUP_EXT}"
    backup_path = Path(BACKUP_DIR) / backup_name
    shutil.make_archive(str(backup_path).replace(APP_BACKUP_EXT, ""), "gztar", APP_DIR)
    print(f"✅ Application backup created: {backup_path}")


def restore_app_backup(backup_file):
    if not Path(backup_file).exists():
        print("❌ Backup file not found.")
        return
    shutil.unpack_archive(str(backup_file), APP_DIR)
    print(f"✅ Application restored from backup: {backup_file}")


def main():
    print("=== NOX Backup & Restore CLI ===")
    backups = list_backups()
    if not backups:
        print("No backups found.")
        return
    print("Available backups:")
    for i, b in enumerate(backups):
        print(f"{i+1}. {b.name}")
    choice = input(
        'Enter backup number to restore, or "n" to create new backup: '
    ).strip()
    if choice.lower() == "n":
        create_app_backup()
    else:
        try:
            idx = int(choice) - 1
            restore_app_backup(backups[idx])
        except Exception:
            print("Invalid selection.")


if __name__ == "__main__":
    main()
