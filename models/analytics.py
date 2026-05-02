"""
Analytics — telemetria anônima (sem PII).

# MELH: Tarefa 4.6 — registra cada busca de rota para dashboard administrativo.
Campos: timestamp, tipo_rota, modo, geocod_ok, tempo_ms, bairro, sucesso.
"""
from __future__ import annotations
import os
import sqlite3
import threading
import time
from typing import Optional

DB_PATH = os.path.join("data", "analytics.db")
TTL_SECONDS = 30 * 24 * 3600


class Analytics:
    _instance: Optional["Analytics"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._init_db()

    @classmethod
    def instance(cls) -> "Analytics":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _conn(self):
        return sqlite3.connect(DB_PATH)

    def _init_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER,
                    tipo_rota TEXT,
                    modo TEXT,
                    geocod_ok INTEGER,
                    tempo_ms INTEGER,
                    bairro TEXT,
                    sucesso INTEGER
                )
            """)

    def log_busca(self, tipo_rota: str, modo: str, geocod_ok: bool,
                  tempo_ms: int, bairro: str, sucesso: bool):
        with self._conn() as c:
            c.execute(
                "INSERT INTO analytics(timestamp,tipo_rota,modo,geocod_ok,tempo_ms,bairro,sucesso) "
                "VALUES (?,?,?,?,?,?,?)",
                (int(time.time()), tipo_rota, modo,
                 1 if geocod_ok else 0, tempo_ms, bairro, 1 if sucesso else 0),
            )

    def get_dashboard_data(self) -> dict:
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM analytics").fetchone()[0]
            sucesso = c.execute("SELECT COUNT(*) FROM analytics WHERE sucesso=1").fetchone()[0]
            tempo_medio = c.execute("SELECT AVG(tempo_ms) FROM analytics").fetchone()[0] or 0

            top_bairros = c.execute(
                "SELECT bairro, COUNT(*) AS n FROM analytics WHERE bairro!='' "
                "GROUP BY bairro ORDER BY n DESC LIMIT 10"
            ).fetchall()

            por_modo = c.execute(
                "SELECT modo, COUNT(*) FROM analytics GROUP BY modo"
            ).fetchall()

        taxa_erro = (1 - sucesso / total) * 100 if total else 0
        return {
            "total": total,
            "taxa_erro_pct": round(taxa_erro, 2),
            "tempo_medio_ms": round(tempo_medio),
            "top_bairros": [{"bairro": b, "n": n} for b, n in top_bairros],
            "por_modo": [{"modo": m, "n": n} for m, n in por_modo],
        }

    def purge_old(self):
        cutoff = int(time.time()) - TTL_SECONDS
        with self._conn() as c:
            c.execute("DELETE FROM analytics WHERE timestamp<?", (cutoff,))
