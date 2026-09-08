"""Idempotently apply the EchoBrief schema.

Reads schema.sql and executes it against the configured Postgres database.
Retries while Postgres is still coming up (useful under docker-compose).

Run standalone:  python init_db.py
"""
import asyncio
import pathlib
import sys

import asyncpg

from app.config import settings

SCHEMA_PATH = pathlib.Path(__file__).parent / "schema.sql"


async def apply_schema() -> None:
    dsn = settings.asyncpg_dsn
    sql = SCHEMA_PATH.read_text(encoding="utf-8")

    last_err: Exception | None = None
    for attempt in range(1, 31):
        try:
            conn = await asyncpg.connect(dsn)
        except Exception as exc:  # noqa: BLE001 - Postgres may not be ready yet
            last_err = exc
            print(f"[init_db] Postgres not ready (attempt {attempt}/30): {exc}")
            await asyncio.sleep(2)
            continue

        try:
            await conn.execute(sql)
            print("[init_db] Schema applied successfully.")
            return
        finally:
            await conn.close()

    print(f"[init_db] Failed to connect to Postgres: {last_err}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(apply_schema())
