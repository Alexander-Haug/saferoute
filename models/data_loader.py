"""
DataLoader (Singleton) — carrega crimes.csv (SSP-SP) em memória.

Schema do CSV: ano, mes, hora, tipo_crime, bairro, latitude, longitude, qtd_ocorrencias

# MELH: Tarefa 2.3 — multiplicador por modo de transporte.
"""
from __future__ import annotations
import csv
import os
import threading
from collections import defaultdict
from typing import Dict, List, Optional


# Tarefa 2.3 — multiplicadores por modo
MODO_MULTIPLIER = {
    "carro": 0.6,
    "bicicleta": 0.9,
    "ape": 1.0,
    "a_pe": 1.0,
    "transporte_publico": 0.8,
}

# Mapeamento de tipos do CSV para grupos de filtro (Tarefa 2.4)
TIPO_GRUPO = {
    "Furto": "roubos_furtos",
    "Roubo": "roubos_furtos",
    "Furto de Veículo": "roubos_furtos",
    "Roubo de Veículo": "roubos_furtos",
    "Homicídio": "homicidios",
    "Lesão Corporal": "violencia",
    "Tráfico de Entorpecentes": "drogas",
}


class DataLoader:
    _instance: Optional["DataLoader"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.records: List[dict] = []
        self.por_bairro: Dict[str, List[dict]] = defaultdict(list)
        self.por_grupo: Dict[str, List[dict]] = defaultdict(list)
        self._centroides: Dict[str, tuple[float, float]] = {}
        self._load()
        self._compute_centroides()

    @classmethod
    def instance(cls) -> "DataLoader":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _load(self):
        path = os.path.join("data", "crimes.csv")
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    rec = {
                        "ano": int(row["ano"]),
                        "mes": int(row["mes"]),
                        "hora": int(row["hora"]),
                        "tipo": row["tipo_crime"].strip(),
                        "bairro": row["bairro"].strip(),
                        "lat": float(row["latitude"]),
                        "lon": float(row["longitude"]),
                        "qtd": int(row["qtd_ocorrencias"]),
                    }
                except (ValueError, KeyError):
                    continue
                rec["grupo"] = TIPO_GRUPO.get(rec["tipo"], "outros")
                self.records.append(rec)
                self.por_bairro[rec["bairro"]].append(rec)
                self.por_grupo[rec["grupo"]].append(rec)

    def _compute_centroides(self):
        agg = defaultdict(lambda: [0.0, 0.0, 0])
        for r in self.records:
            a = agg[r["bairro"]]
            a[0] += r["lat"] * r["qtd"]
            a[1] += r["lon"] * r["qtd"]
            a[2] += r["qtd"]
        self._centroides = {
            b: (slat / n, slon / n) for b, (slat, slon, n) in agg.items() if n > 0
        }

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def calcular_risco(self, via_id: str, hora: int = 12, modo_transporte: str = "ape") -> float:
        """Score 0-10 onde 10 = mais arriscado. via_id = nome do bairro."""
        ocorrencias = self.por_bairro.get(via_id, [])
        if not ocorrencias:
            return 2.0

        total = sum(o["qtd"] for o in ocorrencias)
        # base normalizada — 800 ocorrências ≈ score 10
        base = min(10.0, total / 80.0)

        # ponderação pela faixa horária
        if 0 <= hora < 6:
            fator_hora = 1.4
        elif 6 <= hora < 18:
            fator_hora = 0.85
        else:
            fator_hora = 1.2

        # peso por gravidade dos tipos predominantes
        peso_tipo = 1.0
        homicidios = sum(o["qtd"] for o in ocorrencias if o["tipo"] == "Homicídio")
        roubos = sum(o["qtd"] for o in ocorrencias if o["tipo"].startswith("Roubo"))
        furtos = sum(o["qtd"] for o in ocorrencias if o["tipo"].startswith("Furto"))
        if homicidios > 0:
            peso_tipo += min(0.5, homicidios / 50.0)
        if roubos > furtos:
            peso_tipo += 0.15

        mod = MODO_MULTIPLIER.get(modo_transporte, 1.0)
        score = base * fator_hora * peso_tipo * mod
        return round(min(10.0, max(0.0, score)), 2)

    def get_trend(self, bairro: str):
        """Tendência aproximada com base na distribuição mensal."""
        ocorrencias = self.por_bairro.get(bairro, [])
        if not ocorrencias:
            return (0.0, "estavel")
        por_mes = defaultdict(int)
        for o in ocorrencias:
            por_mes[(o["ano"], o["mes"])] += o["qtd"]
        meses = sorted(por_mes.keys())
        if len(meses) < 2:
            return (0.0, "estavel")
        meio = len(meses) // 2
        a = sum(por_mes[m] for m in meses[:meio])
        b = sum(por_mes[m] for m in meses[meio:])
        if a == 0:
            return (0.0, "estavel")
        delta = (b - a) / a * 100
        direcao = "subindo" if delta > 5 else "descendo" if delta < -5 else "estavel"
        return (round(delta, 1), direcao)

    def centroide_bairro(self, bairro: str) -> Optional[tuple[float, float]]:
        return self._centroides.get(bairro)

    def lista_bairros(self) -> List[dict]:
        out = []
        for bairro in sorted(self.por_bairro.keys()):
            out.append({
                "nome": bairro,
                "score": self.calcular_risco(bairro),
                "ocorrencias": sum(o["qtd"] for o in self.por_bairro[bairro]),
            })
        return out

    # ------------------------------------------------------------------
    # GeoJSON para mapa (Tarefa 2.4)
    # ------------------------------------------------------------------
    def geojson(self, filter_type: str = "all", limit: int = 4000) -> dict:
        feats = []
        for r in self.records:
            if filter_type != "all" and r["grupo"] != filter_type:
                continue
            feats.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                "properties": {
                    "bairro": r["bairro"],
                    "tipo": r["tipo"],
                    "grupo": r["grupo"],
                    "hora": r["hora"],
                    "qtd": r["qtd"],
                    "ano": r["ano"],
                    "mes": r["mes"],
                },
            })
            if len(feats) >= limit:
                break
        return {"type": "FeatureCollection", "features": feats}
