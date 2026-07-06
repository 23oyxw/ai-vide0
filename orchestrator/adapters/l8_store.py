"""L8 metrics persistence — Postgres (production) or SQLite (local fallback)."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from orchestrator.config import settings

logger = logging.getLogger(__name__)

SQLITE_PATH = settings.data_root / "l8_metrics.db"

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS l8_daily_metrics (
    job_id TEXT NOT NULL DEFAULT 'all',
    metric_date TEXT NOT NULL,
    clicks INTEGER NOT NULL DEFAULT 0,
    unique_clicks INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    orders INTEGER NOT NULL DEFAULT 0,
    gmv REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (job_id, metric_date)
);
"""

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS l8_daily_metrics (
    job_id VARCHAR(64) NOT NULL DEFAULT 'all',
    metric_date DATE NOT NULL,
    clicks INTEGER NOT NULL DEFAULT 0,
    unique_clicks INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    orders INTEGER NOT NULL DEFAULT 0,
    gmv NUMERIC(12,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (job_id, metric_date)
);
"""


def resolve_database_url() -> str | None:
    for candidate in (
        settings.postgres_url,
        settings.database_url,
    ):
        if candidate and str(candidate).strip():
            return str(candidate).strip()
    return None


def data_source_label() -> str:
    url = resolve_database_url()
    if url:
        if url.startswith("postgresql") or url.startswith("postgres"):
            return "postgres"
        return "database_url"
    if SQLITE_PATH.exists():
        return "sqlite"
    return "demo"


def is_persistent_store() -> bool:
    return data_source_label() in ("postgres", "database_url", "sqlite")


@contextmanager
def _sqlite_conn() -> Iterator[sqlite3.Connection]:
    settings.data_root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init_sqlite() -> None:
    with _sqlite_conn() as conn:
        conn.executescript(SCHEMA_SQLITE)
        row = conn.execute("SELECT COUNT(*) AS c FROM l8_daily_metrics").fetchone()
        if row and row["c"] == 0:
            _seed_rows_sqlite(conn)


def _seed_rows_sqlite(conn: sqlite3.Connection) -> None:
    rows = [
        ("all", "2026-07-01", 4200, 3100, 186, 102, 20398.0),
        ("all", "2026-07-02", 4800, 3600, 210, 118, 23456.0),
        ("all", "2026-07-03", 5100, 3800, 228, 125, 24890.0),
        ("demo", "2026-07-03", 1200, 900, 54, 28, 5566.0),
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO l8_daily_metrics
        (job_id, metric_date, clicks, unique_clicks, conversions, orders, gmv)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _fetch_postgres(job_id: str | None) -> dict[str, float] | None:
    url = resolve_database_url()
    if not url:
        return None
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        logger.warning("psycopg not installed — pip install psycopg[binary]")
        return None

    jid = job_id or "all"
    try:
        with psycopg.connect(url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_POSTGRES)
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(clicks), 0) AS clicks,
                        COALESCE(SUM(unique_clicks), 0) AS unique_clicks,
                        COALESCE(SUM(conversions), 0) AS conversions,
                        COALESCE(SUM(orders), 0) AS orders,
                        COALESCE(SUM(gmv), 0) AS gmv
                    FROM l8_daily_metrics
                    WHERE job_id = %s OR %s = 'all'
                    """,
                    (jid, jid),
                )
                row = cur.fetchone()
                if not row or int(row["clicks"] or 0) == 0:
                    if jid != "all":
                        cur.execute(
                            """
                            SELECT
                                COALESCE(SUM(clicks), 0) AS clicks,
                                COALESCE(SUM(unique_clicks), 0) AS unique_clicks,
                                COALESCE(SUM(conversions), 0) AS conversions,
                                COALESCE(SUM(orders), 0) AS orders,
                                COALESCE(SUM(gmv), 0) AS gmv
                            FROM l8_daily_metrics
                            WHERE job_id = 'all'
                            """
                        )
                        row = cur.fetchone()
                if not row:
                    return None
                clicks = float(row["clicks"] or 0)
                unique = float(row["unique_clicks"] or 0)
                conversions = float(row["conversions"] or 0)
                return {
                    "clicks": clicks,
                    "unique_clicks": unique,
                    "ctr": round(clicks / max(unique * 25, 1), 4),
                    "conversions": conversions,
                    "conversion_rate": round(conversions / max(unique, 1), 4),
                    "orders": float(row["orders"] or 0),
                    "gmv": float(row["gmv"] or 0),
                }
    except Exception as exc:
        logger.warning("postgres l8 fetch failed: %s", exc)
        return None


def _fetch_sqlite(job_id: str | None) -> dict[str, float] | None:
    _init_sqlite()
    jid = job_id or "all"
    with _sqlite_conn() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(clicks), 0) AS clicks,
                COALESCE(SUM(unique_clicks), 0) AS unique_clicks,
                COALESCE(SUM(conversions), 0) AS conversions,
                COALESCE(SUM(orders), 0) AS orders,
                COALESCE(SUM(gmv), 0) AS gmv
            FROM l8_daily_metrics
            WHERE job_id = ? OR ? = 'all'
            """,
            (jid, jid),
        ).fetchone()
        if not row or int(row["clicks"] or 0) == 0:
            return None
        clicks = float(row["clicks"])
        unique = float(row["unique_clicks"])
        conversions = float(row["conversions"])
        return {
            "clicks": clicks,
            "unique_clicks": unique,
            "ctr": round(clicks / max(unique * 25, 1), 4),
            "conversions": conversions,
            "conversion_rate": round(conversions / max(unique, 1), 4),
            "orders": float(row["orders"]),
            "gmv": float(row["gmv"]),
        }


def fetch_aggregated_metrics(job_id: str | None = None) -> dict[str, float] | None:
    """Return L8 KPI aggregate from Postgres or SQLite; None → caller uses demo."""
    pg = _fetch_postgres(job_id)
    if pg:
        return pg
    return _fetch_sqlite(job_id)


def upsert_daily_metrics(
    *,
    job_id: str,
    metric_date: str,
    clicks: int,
    unique_clicks: int,
    conversions: int,
    orders: int,
    gmv: float,
) -> str:
    """Insert or replace one daily row. Returns backend: postgres | sqlite."""
    url = resolve_database_url()
    if url and (url.startswith("postgresql") or url.startswith("postgres")):
        try:
            import psycopg

            with psycopg.connect(url) as conn:
                with conn.cursor() as cur:
                    cur.execute(SCHEMA_POSTGRES)
                    cur.execute(
                        """
                        INSERT INTO l8_daily_metrics
                        (job_id, metric_date, clicks, unique_clicks, conversions, orders, gmv)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (job_id, metric_date) DO UPDATE SET
                          clicks = EXCLUDED.clicks,
                          unique_clicks = EXCLUDED.unique_clicks,
                          conversions = EXCLUDED.conversions,
                          orders = EXCLUDED.orders,
                          gmv = EXCLUDED.gmv
                        """,
                        (
                            job_id,
                            metric_date,
                            clicks,
                            unique_clicks,
                            conversions,
                            orders,
                            gmv,
                        ),
                    )
                conn.commit()
            return "postgres"
        except Exception as exc:
            logger.warning("postgres upsert failed (%s), fallback sqlite", exc)

    _init_sqlite()
    with _sqlite_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO l8_daily_metrics
            (job_id, metric_date, clicks, unique_clicks, conversions, orders, gmv)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, metric_date, clicks, unique_clicks, conversions, orders, gmv),
        )
    return "sqlite"


def init_local_store() -> str:
    """Ensure SQLite schema + seed exist; return source label."""
    url = resolve_database_url()
    if url and (url.startswith("postgresql") or url.startswith("postgres")):
        try:
            import psycopg

            with psycopg.connect(url) as conn:
                with conn.cursor() as cur:
                    cur.execute(SCHEMA_POSTGRES)
            return "postgres"
        except Exception as exc:
            logger.warning("postgres init failed (%s), falling back to sqlite", exc)
    _init_sqlite()
    return "sqlite"


def export_metrics_documents(job_id: str | None = None) -> list[dict[str, Any]]:
    """Export rows as RAG documents for /rag/ingest source=database."""
    _init_sqlite()
    jid = job_id or "all"
    docs: list[dict[str, Any]] = []
    with _sqlite_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM l8_daily_metrics WHERE job_id = ? OR ? = 'all' ORDER BY metric_date",
            (jid, jid),
        ).fetchall()
        for row in rows:
            text = (
                f"job={row['job_id']} date={row['metric_date']} "
                f"clicks={row['clicks']} conversions={row['conversions']} "
                f"orders={row['orders']} gmv={row['gmv']}"
            )
            docs.append({"text": text, "metadata": dict(row)})
    return docs
