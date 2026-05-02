"""
SafeRouteFacade — orquestra DataLoader, Geocoding e cache.

Padrão Façade: esconde detalhes do scoring, geocoding e cálculo de rotas
expondo uma API simples ao controller.
"""
from __future__ import annotations
import math
import secrets
import time
from typing import Optional

import requests

from models.data_loader import DataLoader
from models.geocoding_cache import GeocodeCache


# Storage simples in-memory de rotas compartilhadas — Tarefa 2.6
_SHARED_ROUTES: dict[str, dict] = {}


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class SafeRouteFacade:
    def __init__(self):
        self.loader = DataLoader.instance()
        self.cache = GeocodeCache.instance()

    # ---------------- Geocoding (Nominatim + cache) — Tarefa 4.5
    def geocode(self, endereco: str) -> Optional[tuple[float, float]]:
        if not endereco:
            return None
        cached = self.cache.get(endereco)
        if cached:
            return cached
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"{endereco}, São Paulo, Brasil", "format": "json", "limit": 1},
                headers={"User-Agent": "SafeRoute-PUC-SP/2.0"},
                timeout=8,
            )
            if resp.ok and resp.json():
                d = resp.json()[0]
                lat, lon = float(d["lat"]), float(d["lon"])
                self.cache.set(endereco, lat, lon)
                return (lat, lon)
        except Exception:
            return None
        return None

    def reverse_geocode(self, lat: float, lon: float) -> str:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers={"User-Agent": "SafeRoute-PUC-SP/2.0"},
                timeout=8,
            )
            if resp.ok:
                return resp.json().get("display_name", f"{lat:.5f}, {lon:.5f}")
        except Exception:
            pass
        return f"{lat:.5f}, {lon:.5f}"

    # ---------------- Scoring delegado ao DataLoader
    def calcular_risco(self, via_id: str, hora: int = 12, modo: str = "ape") -> float:
        return self.loader.calcular_risco(via_id, hora, modo)

    def get_trend(self, bairro: str):
        return self.loader.get_trend(bairro)

    # ---------------- Rotas (3 alternativas) — Tarefa 1.2
    def get_route_details(self, origem: str, destino: str, horario_iso: str,
                          prioridade: str = "equilibrada", modo: str = "ape") -> dict:
        o = self.geocode(origem)
        d = self.geocode(destino)
        if not o or not d:
            return {"erro": "Não foi possível localizar origem ou destino.", "rotas": []}

        try:
            hora = int(horario_iso.split("T")[1].split(":")[0])
        except Exception:
            hora = 12

        bairro_o = self._nearest_bairro(*o)
        bairro_d = self._nearest_bairro(*d)

        dist_km = _haversine_km(o[0], o[1], d[0], d[1])
        velocidade = {"carro": 30, "transporte_publico": 20, "bicicleta": 15, "ape": 5}.get(modo, 15)
        tempo_min = max(1, round(dist_km / velocidade * 60))

        risco_o = self.calcular_risco(bairro_o, hora, modo)
        risco_d = self.calcular_risco(bairro_d, hora, modo)
        risco = (risco_o + risco_d) / 2

        # Geometrias didáticas: 3 variações com offsets sutis no ponto médio
        def linha(off_lat, off_lon):
            mid = ((o[0] + d[0]) / 2 + off_lat, (o[1] + d[1]) / 2 + off_lon)
            return [[o[1], o[0]], [mid[1], mid[0]], [d[1], d[0]]]

        rotas = [
            {
                "id": "A", "label": "Mais segura", "cor": "#10B981",
                "score_risco": round(max(0.5, risco - 1.5), 2),
                "distancia_km": round(dist_km * 1.15, 2),
                "tempo_min": round(tempo_min * 1.2),
                "resumo": "Evita áreas com mais ocorrências; pode ser mais longa.",
                "geometria": linha(0.005, -0.005),
            },
            {
                "id": "B", "label": "Equilibrada", "cor": "#3B82F6",
                "score_risco": round(risco, 2),
                "distancia_km": round(dist_km * 1.05, 2),
                "tempo_min": round(tempo_min * 1.05),
                "resumo": "Bom compromisso entre segurança e tempo.",
                "geometria": linha(0.0, 0.0),
            },
            {
                "id": "C", "label": "Mais rápida", "cor": "#F97316",
                "score_risco": round(min(10.0, risco + 1.5), 2),
                "distancia_km": round(dist_km, 2),
                "tempo_min": tempo_min,
                "resumo": "Trajeto direto; pode atravessar áreas sensíveis.",
                "geometria": linha(-0.005, 0.005),
            },
        ]
        recomendada = {"segura": "A", "rapida": "C"}.get(prioridade, "B")
        trend_pct, trend_dir = self.get_trend(bairro_d)

        return {
            "erro": None,
            "origem": {"endereco": origem, "lat": o[0], "lon": o[1], "bairro": bairro_o},
            "destino": {"endereco": destino, "lat": d[0], "lon": d[1], "bairro": bairro_d},
            "modo": modo, "horario": horario_iso, "prioridade": prioridade,
            "recomendada": recomendada, "rotas": rotas,
            "tendencia_destino": {"percentual": trend_pct, "direcao": trend_dir},
        }

    def _nearest_bairro(self, lat: float, lon: float) -> str:
        best, best_d = None, 1e9
        for bairro, (clat, clon) in self.loader._centroides.items():
            d = _haversine_km(lat, lon, clat, clon)
            if d < best_d:
                best_d, best = d, bairro
        return best or "Sé"

    # ---------------- Mapa GeoJSON com filtros — Tarefa 2.4
    def get_map_geojson(self, filter_type: str = "all") -> dict:
        return self.loader.geojson(filter_type)

    # ---------------- Compartilhar — Tarefa 2.6
    def compartilhar(self, payload: dict) -> str:
        token = secrets.token_urlsafe(8)
        _SHARED_ROUTES[token] = {"payload": payload, "ts": int(time.time())}
        return token

    def recuperar_compartilhada(self, token: str) -> Optional[dict]:
        entry = _SHARED_ROUTES.get(token)
        return entry["payload"] if entry else None
