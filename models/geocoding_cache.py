"""
GeocodeCache — cache local SQLite com fuzzy match para geocodificação.

# MELH: Tarefa 4.5 — evita reconsultar Nominatim para endereços parecidos.
Estratégia:
  1. Busca exata por endereço normalizado.
  2. Se não houver, fuzzy match com difflib (similaridade > 0.9) em registros < 30 dias.
"""
from __future__ import annotations
import os
import sqlite3
import threading
import time
from difflib import SequenceMatcher
from typing import Optional, Tuple

DB_PATH = os.path.join("data", "geocode_cache.db")
TTL_SECONDS = 30 * 24 * 3600  # 30 dias
SIMILARITY_THRESHOLD = 0.90


def _normalize(s: str) -> str:
    return " ".join(s.lower().strip().split())


class GeocodeCache:
    _instance: Optional["GeocodeCache"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._init_db()

    @classmethod
    def instance(cls) -> "GeocodeCache":
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
                CREATE TABLE IF NOT EXISTS geocoding_cache (
                    endereco_input TEXT PRIMARY KEY,
                    lat REAL,
                    lon REAL,
                    timestamp INTEGER
                )
            """)

    def get(self, endereco: str) -> Optional[Tuple[float, float]]:
        if not endereco:
            return None
        norm = _normalize(endereco)
        cutoff = int(time.time()) - TTL_SECONDS
        with self._conn() as c:
            # 1) match exato
            row = c.execute(
                "SELECT lat, lon FROM geocoding_cache WHERE endereco_input=? AND timestamp>?",
                (norm, cutoff),
            ).fetchone()
            if row:
                return (row[0], row[1])

            # 2) fuzzy match
            rows = c.execute(
                "SELECT endereco_input, lat, lon FROM geocoding_cache WHERE timestamp>?",
                (cutoff,),
            ).fetchall()
            best = None
            best_score = 0.0
            for end_in, lat, lon in rows:
                score = SequenceMatcher(None, norm, end_in).ratio()
                if score > best_score:
                    best_score = score
                    best = (lat, lon)
            if best and best_score >= SIMILARITY_THRESHOLD:
                return best
        return None

    def set(self, endereco: str, lat: float, lon: float):
        if not endereco:
            return
        norm = _normalize(endereco)
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO geocoding_cache(endereco_input, lat, lon, timestamp) VALUES (?,?,?,?)",
                (norm, lat, lon, int(time.time())),
            )

    def purge_old(self):
        cutoff = int(time.time()) - TTL_SECONDS
        with self._conn() as c:
            c.execute("DELETE FROM geocoding_cache WHERE timestamp<?", (cutoff,))
