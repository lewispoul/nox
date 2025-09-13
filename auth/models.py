"""
Modèles de données pour l'authentification et les utilisateurs
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

# Configuration de la base de données
DB_PATH = Path(os.getenv("NOX_DB_PATH", f"{Path(__file__).parent.parent}/data/nox.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class UserRole:
    ADMIN = "admin"
    USER = "user"

    @classmethod
    def all_roles(cls) -> List[str]:
        return [cls.ADMIN, cls.USER]

    @classmethod
    def is_valid_role(cls, role: str) -> bool:
        return role in cls.all_roles()


class User:
    """Modèle utilisateur pour la base de données"""

    def __init__(
        self,
        id: str,
        email: str,
        hashed_password: str,
        role: str = UserRole.USER,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        quota_files: int = 100,
        quota_cpu_seconds: int = 3600,
        quota_memory_mb: int = 512,
    ):
        self.id = id
        self.email = email
        self.hashed_password = hashed_password
        self.role = role
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.quota_files = quota_files
        self.quota_cpu_seconds = quota_cpu_seconds
        self.quota_memory_mb = quota_memory_mb

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour sérialisation"""
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "quota_files": self.quota_files,
            "quota_cpu_seconds": self.quota_cpu_seconds,
            "quota_memory_mb": self.quota_memory_mb,
        }


class Database:
    """Gestionnaire de base de données SQLite pour les utilisateurs"""

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path

    async def init_db(self):
        """Initialise la base de données et crée les tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    quota_files INTEGER NOT NULL DEFAULT 100,
                    quota_cpu_seconds INTEGER NOT NULL DEFAULT 3600,
                    quota_memory_mb INTEGER NOT NULL DEFAULT 512
                )
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_role ON users (role)
            """
            )

            await db.commit()

    async def create_user(self, user: User) -> User:
        """Crée un nouvel utilisateur"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (
                    id, email, hashed_password, role, is_active, 
                    created_at, quota_files, quota_cpu_seconds, quota_memory_mb
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user.id,
                    user.email,
                    user.hashed_password,
                    user.role,
                    user.is_active,
                    user.created_at.isoformat(),
                    user.quota_files,
                    user.quota_cpu_seconds,
                    user.quota_memory_mb,
                ),
            )
            await db.commit()
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Récupère un utilisateur par email"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_user(row)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Récupère un utilisateur par ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_user(row)
        return None

    async def update_user(self, user: User) -> User:
        """Met à jour un utilisateur"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE users SET
                    email = ?, role = ?, is_active = ?,
                    quota_files = ?, quota_cpu_seconds = ?, quota_memory_mb = ?
                WHERE id = ?
            """,
                (
                    user.email,
                    user.role,
                    user.is_active,
                    user.quota_files,
                    user.quota_cpu_seconds,
                    user.quota_memory_mb,
                    user.id,
                ),
            )
            await db.commit()
        return user

    async def list_users(self, limit: int = 50, offset: int = 0) -> List[User]:
        """Liste tous les utilisateurs avec pagination"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_user(row) for row in rows]

    async def delete_user(self, user_id: str) -> bool:
        """Supprime un utilisateur"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            await db.commit()
            return cursor.rowcount > 0

    def _row_to_user(self, row) -> User:
        """Convertit une ligne de base de données en objet User"""
        return User(
            id=row[0],
            email=row[1],
            hashed_password=row[2],
            role=row[3],
            is_active=bool(row[4]),
            created_at=datetime.fromisoformat(row[5]) if row[5] else None,
            quota_files=row[6],
            quota_cpu_seconds=row[7],
            quota_memory_mb=row[8],
        )


# Instance globale de la base de données
db = Database()
