"""
Database migrations for PostgreSQL quota system
"""

import asyncio
import os
from typing import Optional

import asyncpg


class PostgreSQLMigrations:
    """Gestionnaire de migrations PostgreSQL pour le système de quotas"""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Construit la chaîne de connexion PostgreSQL"""
        # Depuis les variables d'environnement Docker
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "noxdb")
        user = os.getenv("POSTGRES_USER", "noxuser")
        password = os.getenv("POSTGRES_PASSWORD", "test_password_123")

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    async def connect(self):
        """Crée une connexion à la base de données"""
        return await asyncpg.connect(self.connection_string)

    async def create_migrations_table(self):
        """Crée la table de suivi des migrations"""
        conn = await self.connect()
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT NOW()
                )
            """
            )
        finally:
            await conn.close()

    async def has_migration(self, migration_name: str) -> bool:
        """Vérifie si une migration a déjà été appliquée"""
        conn = await self.connect()
        try:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM migrations WHERE migration_name = $1",
                migration_name,
            )
            return result > 0
        finally:
            await conn.close()

    async def record_migration(self, migration_name: str):
        """Enregistre qu'une migration a été appliquée"""
        conn = await self.connect()
        try:
            await conn.execute(
                "INSERT INTO migrations (migration_name) VALUES ($1)", migration_name
            )
        finally:
            await conn.close()

    async def migrate_users_table(self):
        """Migration: Ajouter les colonnes de quotas à la table users"""
        migration_name = "add_user_quotas"

        if await self.has_migration(migration_name):
            print(f"Migration {migration_name} already applied, skipping...")
            return

        conn = await self.connect()
        try:
            # Créer la table users si elle n'existe pas
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'user',
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
            )

            # Ajouter les colonnes de quotas
            await conn.execute(
                """
                ALTER TABLE users
                  ADD COLUMN IF NOT EXISTS quota_req_hour INTEGER DEFAULT 100,
                  ADD COLUMN IF NOT EXISTS quota_req_day INTEGER DEFAULT 1000,
                  ADD COLUMN IF NOT EXISTS quota_cpu_seconds INTEGER DEFAULT 300,
                  ADD COLUMN IF NOT EXISTS quota_mem_mb INTEGER DEFAULT 512,
                  ADD COLUMN IF NOT EXISTS quota_storage_mb INTEGER DEFAULT 100,
                  ADD COLUMN IF NOT EXISTS quota_files_max INTEGER DEFAULT 50
            """
            )

            await self.record_migration(migration_name)
            print(f"✅ Migration {migration_name} applied successfully")

        except Exception as e:
            print(f"❌ Migration {migration_name} failed: {e}")
            raise
        finally:
            await conn.close()

    async def create_user_usage_table(self):
        """Migration: Créer la table user_usage"""
        migration_name = "create_user_usage"

        if await self.has_migration(migration_name):
            print(f"Migration {migration_name} already applied, skipping...")
            return

        conn = await self.connect()
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_usage (
                    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    req_hour INTEGER DEFAULT 0,
                    req_day INTEGER DEFAULT 0,
                    cpu_seconds BIGINT DEFAULT 0,
                    mem_peak_mb INTEGER DEFAULT 0,
                    storage_mb INTEGER DEFAULT 0,
                    files_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """
            )

            # Index pour les requêtes fréquentes
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_usage_updated_at 
                ON user_usage (updated_at)
            """
            )

            await self.record_migration(migration_name)
            print(f"✅ Migration {migration_name} applied successfully")

        except Exception as e:
            print(f"❌ Migration {migration_name} failed: {e}")
            raise
        finally:
            await conn.close()

    async def create_quota_violations_table(self):
        """Migration: Créer la table quota_violations"""
        migration_name = "create_quota_violations"

        if await self.has_migration(migration_name):
            print(f"Migration {migration_name} already applied, skipping...")
            return

        conn = await self.connect()
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quota_violations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    reason TEXT NOT NULL,
                    detail JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
            )

            # Index pour les requêtes de monitoring
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_quota_violations_user_id 
                ON quota_violations (user_id)
            """
            )

            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_quota_violations_created_at 
                ON quota_violations (created_at)
            """
            )

            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_quota_violations_reason 
                ON quota_violations (reason)
            """
            )

            await self.record_migration(migration_name)
            print(f"✅ Migration {migration_name} applied successfully")

        except Exception as e:
            print(f"❌ Migration {migration_name} failed: {e}")
            raise
        finally:
            await conn.close()

    async def run_all_migrations(self):
        """Exécute toutes les migrations dans l'ordre"""
        print("🚀 Starting database migrations...")

        try:
            # Créer la table de migrations en premier
            await self.create_migrations_table()

            # Exécuter les migrations dans l'ordre
            await self.migrate_users_table()
            await self.create_user_usage_table()
            await self.create_quota_violations_table()

            print("✅ All migrations completed successfully")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise


async def run_migrations():
    """Point d'entrée pour exécuter les migrations"""
    migrations = PostgreSQLMigrations()
    await migrations.run_all_migrations()


if __name__ == "__main__":
    asyncio.run(run_migrations())
