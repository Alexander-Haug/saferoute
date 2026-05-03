"""
SafeRouteFacade — orquestra geocoding (Mapbox + Nominatim fallback),
roteamento real (Mapbox Directions com alternatives) e scoring de risco.

# v2.1 — Bugs 1, 3, 4: rotas reais via Mapbox Directions, geocoding com
# proximity SP e country=BR, scoring por trajeto sampling.
"""
from __future__ import annotations
import math
import os
import secrets
import time
from typing import Optional

import requests

from models.data_loader import DataLoader
from models.geocoding_cache import GeocodeCache


_SHARED_ROUTES: dict[str, dict] = {}

# Centro de São Paulo — usado como proximity hint pra geocoding
SP_CENTER = (-46.6333, -23.5505)  # (lon, lat)

# Mapeamento modo → profile da Mapbox Directions API
MODO_PROFILE = {
    "ape": "walking",
    "a_pe": "walking",
    "bicicleta": "cycling",
    "carro": "driving",
    "transporte_publico": "driving-traffic",  # melhor proxy disponível
}


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _mapbox_token() -> str:
    return os.environ.get("MAPBOX_TOKEN", "")


class SafeRouteFacade:
    def __init__(self):
        self.loader = DataLoader.instance()
        self.cache = GeocodeCache.instance()

    # ──────────────────────────────────────────────────────────────────
    # GEOCODING — Bug 1
    # Mapbox Geocoding API com proximity em SP + country=BR.
    # Fallback pro Nominatim (sem custo) caso o token Mapbox falte ou falhe.
    # ──────────────────────────────────────────────────────────────────
    def geocode(self, endereco: str) -> Optional[tuple[float, float]]:
        if not endereco or len(endereco.strip()) < 4:
            return None

        cached = self.cache.get(endereco)
        if cached:
            return cached

        token = _mapbox_token()
        if token:
            try:
                # Endereço URL-encoded; Mapbox aceita slashes ok
                from urllib.parse import quote
                q = quote(endereco.strip(), safe="")
                url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{q}.json"
                resp = requests.get(url, params={
                    "access_token": token,
                    "country": "BR",
                    "proximity": f"{SP_CENTER[0]},{SP_CENTER[1]}",
                    "limit": 1,
                    "language": "pt",
                    # Restringe à bbox do município de São Paulo (W,S,E,N)
                    "bbox": "-46.83,-24.01,-46.36,-23.36",
                }, timeout=8)
                if resp.ok:
                    feats = resp.json().get("features", [])
                    if feats:
                        lon, lat = feats[0]["center"]
                        self.cache.set(endereco, lat, lon)
                        return (lat, lon)
            except Exception:
                pass  # cai pro fallback

        # Fallback Nominatim (mais lento, sem proximity tão preciso)
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": f"{endereco}, São Paulo, SP, Brasil",
                    "format": "json", "limit": 1,
                    "countrycodes": "br",
                    "viewbox": "-46.83,-23.36,-46.36,-24.01",
                    "bounded": 1,
                },
                headers={"User-Agent": "SafeRoute-PUC-SP/2.1"},
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

    def suggest(self, query: str, limit: int = 5) -> list[dict]:
        """Sugestões de endereço pra autocomplete (Mapbox Geocoding com bbox SP).
        Retorna [{label, lat, lon, bairro?}, ...]."""
        q = (query or "").strip()
        if len(q) < 3:
            return []
        token = _mapbox_token()
        if not token:
            return []
        try:
            from urllib.parse import quote
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(q, safe='')}.json"
            resp = requests.get(url, params={
                "access_token": token,
                "country": "BR",
                "proximity": f"{SP_CENTER[0]},{SP_CENTER[1]}",
                "bbox": "-46.83,-24.01,-46.36,-23.36",
                "limit": limit,
                "language": "pt",
                "autocomplete": "true",
                "types": "address,poi,neighborhood,place",
            }, timeout=4)
            if not resp.ok:
                return []
            out = []
            for f in resp.json().get("features", []):
                lon, lat = f["center"]
                out.append({
                    "label": f.get("place_name", q),
                    "text": f.get("text", ""),
                    "lat": lat, "lon": lon,
                })
            return out
        except Exception:
            return []

    def reverse_geocode(self, lat: float, lon: float) -> str:
        token = _mapbox_token()
        if token:
            try:
                resp = requests.get(
                    f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lon},{lat}.json",
                    params={"access_token": token, "language": "pt", "limit": 1},
                    timeout=6,
                )
                if resp.ok:
                    feats = resp.json().get("features", [])
                    if feats:
                        return feats[0].get("place_name", f"{lat:.5f}, {lon:.5f}")
            except Exception:
                pass
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers={"User-Agent": "SafeRoute-PUC-SP/2.1"},
                timeout=6,
            )
            if resp.ok:
                return resp.json().get("display_name", f"{lat:.5f}, {lon:.5f}")
        except Exception:
            pass
        return f"{lat:.5f}, {lon:.5f}"

    # ──────────────────────────────────────────────────────────────────
    # SCORING
    # ──────────────────────────────────────────────────────────────────
    def calcular_risco(self, via_id: str, hora: int = 12, modo: str = "ape") -> float:
        return self.loader.calcular_risco(via_id, hora, modo)

    def get_trend(self, bairro: str):
        return self.loader.get_trend(bairro)

    def _score_trajeto(self, coords_lonlat: list[list[float]], hora: int, modo: str) -> tuple[float, str]:
        """Sample N pontos ao longo da rota e retorna (score_medio, bairro_pior)."""
        if not coords_lonlat:
            return 5.0, "Sé"
        n = min(12, max(3, len(coords_lonlat) // 20))
        step = max(1, len(coords_lonlat) // n)
        amostras = coords_lonlat[::step]
        scores = []
        bairros_count = {}
        bairro_pior, score_pior = "Sé", -1.0
        for lon, lat in amostras:
            bairro = self._nearest_bairro(lat, lon)
            s = self.calcular_risco(bairro, hora, modo)
            scores.append(s)
            bairros_count[bairro] = bairros_count.get(bairro, 0) + 1
            if s > score_pior:
                score_pior, bairro_pior = s, bairro
        media = sum(scores) / len(scores) if scores else 5.0
        return round(media, 2), bairro_pior

    # ──────────────────────────────────────────────────────────────────
    # ROTAS — Bugs 3, 4: Mapbox Directions com alternatives
    # ──────────────────────────────────────────────────────────────────
    def _mapbox_directions(self, o: tuple[float, float], d: tuple[float, float],
                           profile: str) -> list[dict]:
        """Retorna lista de rotas reais (até 3) da Mapbox Directions.
        Cada rota: {"distance": m, "duration": s, "geometry": {...GeoJSON LineString}}.
        """
        token = _mapbox_token()
        if not token:
            return []
        # coordenadas no formato lon,lat;lon,lat
        coords = f"{o[1]},{o[0]};{d[1]},{d[0]}"
        url = f"https://api.mapbox.com/directions/v5/mapbox/{profile}/{coords}"
        try:
            resp = requests.get(url, params={
                "access_token": token,
                "alternatives": "true",
                "geometries": "geojson",
                "overview": "full",
                "language": "pt",
            }, timeout=10)
            if resp.ok:
                return resp.json().get("routes", [])
        except Exception:
            return []
        return []

    def get_route_details(self, origem: str, destino: str, horario_iso: str,
                          prioridade: str = "equilibrada", modo: str = "ape") -> dict:
        # Validação prévia (Bug 5)
        if not origem or len(origem.strip()) < 4:
            return {"erro": "Origem inválida — informe um endereço com pelo menos 4 caracteres.",
                    "campo_erro": "origem", "rotas": []}
        if not destino or len(destino.strip()) < 4:
            return {"erro": "Destino inválido — informe um endereço com pelo menos 4 caracteres.",
                    "campo_erro": "destino", "rotas": []}

        o = self.geocode(origem)
        d = self.geocode(destino)
        if not o:
            return {"erro": "Não consegui localizar a ORIGEM. Tente um formato como "
                            "'Av. Paulista, 1578 - São Paulo, SP'.",
                    "campo_erro": "origem", "rotas": []}
        if not d:
            return {"erro": "Não consegui localizar o DESTINO. Tente um formato como "
                            "'Rua Augusta, 500 - São Paulo, SP'.",
                    "campo_erro": "destino", "rotas": []}

        # Sanidade: distância > 80 km dentro de SP é provavelmente bug de geocoding
        dist_total = _haversine_km(o[0], o[1], d[0], d[1])
        if dist_total > 80:
            return {"erro": "Distância suspeita (>80 km). Talvez um dos endereços tenha sido "
                            "interpretado fora de São Paulo. Tente incluir 'São Paulo, SP'.",
                    "campo_erro": "ambos", "rotas": []}

        try:
            hora = int(horario_iso.split("T")[1].split(":")[0])
        except Exception:
            hora = 12

        bairro_o = self._nearest_bairro(*o)
        bairro_d = self._nearest_bairro(*d)
        profile = MODO_PROFILE.get(modo, "walking")

        # 1) Pega alternativas REAIS da Mapbox — não sintetiza nada.
        #    Se vier 1, mostra 1; se vier 2, mostra 2; se vier 3, mostra 3.
        mb_routes = self._mapbox_directions(o, d, profile)

        # 2) Fallback didático só se Mapbox falhou completamente (sem rede/token)
        if not mb_routes:
            return self._rotas_fallback(o, d, origem, destino, modo, prioridade,
                                        horario_iso, hora, bairro_o, bairro_d, dist_total)

        # 3) Calcula score por trajeto (sample de pontos) e tempo/distância reais
        enriched = []
        for r in mb_routes[:3]:
            coords = r["geometry"]["coordinates"]  # [[lon,lat], ...]
            score, bairro_pior = self._score_trajeto(coords, hora, modo)
            enriched.append({
                "score": score, "bairro_pior": bairro_pior,
                "distancia_km": round(r["distance"] / 1000, 2),
                "tempo_min": max(1, round(r["duration"] / 60)),
                "geometria": coords,
            })

        # 4) Etiqueta as rotas por funcionalidade (ocorrências + distância)
        rotas, recomendada = self._etiquetar_rotas(enriched, prioridade)
        trend_pct, trend_dir = self.get_trend(bairro_d)

        return {
            "erro": None,
            "origem": {"endereco": origem, "lat": o[0], "lon": o[1], "bairro": bairro_o},
            "destino": {"endereco": destino, "lat": d[0], "lon": d[1], "bairro": bairro_d},
            "modo": modo, "horario": horario_iso, "prioridade": prioridade,
            "recomendada": recomendada, "rotas": rotas,
            "tendencia_destino": {"percentual": trend_pct, "direcao": trend_dir},
        }

    def _etiquetar_rotas(self, enriched: list[dict], prioridade: str) -> tuple[list[dict], str]:
        """Decide labels (Mais segura / Equilibrada / Mais rápida) com base
        em ocorrências (score) e distância (tempo). Mostra só o que veio:
        1 → "Rota disponível"; 2 → "Mais segura" + "Mais rápida"; 3 → as três."""
        # Combina score (peso 0.6) e tempo normalizado (peso 0.4) pro ranking
        n = len(enriched)
        if n == 1:
            r = enriched[0]
            rotas = [{
                "id": "B", "label": "Rota disponível", "cor": "#3B82F6",
                "score_risco": r["score"],
                "distancia_km": r["distancia_km"], "tempo_min": r["tempo_min"],
                "resumo": f"Única rota retornada pelo Mapbox para este trecho. "
                          f"Pior trecho: {r['bairro_pior']}.",
                "geometria": r["geometria"],
            }]
            return rotas, "B"

        # Para 2+ rotas: ordena por score (asc) e por tempo (asc)
        by_score = sorted(enriched, key=lambda x: x["score"])
        by_time = sorted(enriched, key=lambda x: x["tempo_min"])
        segura = by_score[0]
        rapida = by_time[0]

        if n == 2:
            # Pode acontecer das duas serem o mesmo objeto se a mais segura
            # também é a mais rápida — nesse caso, etiqueta só 2 distintas
            if segura is rapida:
                # Pega a outra como segunda alternativa
                outra = [x for x in enriched if x is not segura][0]
                rotas = [
                    {"id": "A", "label": "Mais segura e mais rápida", "cor": "#10B981",
                     "score_risco": segura["score"],
                     "distancia_km": segura["distancia_km"], "tempo_min": segura["tempo_min"],
                     "resumo": f"Vence em ambos critérios. Pior trecho: {segura['bairro_pior']}.",
                     "geometria": segura["geometria"]},
                    {"id": "C", "label": "Alternativa", "cor": "#F97316",
                     "score_risco": outra["score"],
                     "distancia_km": outra["distancia_km"], "tempo_min": outra["tempo_min"],
                     "resumo": "Outro trajeto possível para comparação.",
                     "geometria": outra["geometria"]},
                ]
                return rotas, "A"
            rotas = [
                {"id": "A", "label": "Mais segura", "cor": "#10B981",
                 "score_risco": segura["score"],
                 "distancia_km": segura["distancia_km"], "tempo_min": segura["tempo_min"],
                 "resumo": f"Menor exposição a ocorrências. Pior trecho: {segura['bairro_pior']}.",
                 "geometria": segura["geometria"]},
                {"id": "C", "label": "Mais rápida", "cor": "#F97316",
                 "score_risco": rapida["score"],
                 "distancia_km": rapida["distancia_km"], "tempo_min": rapida["tempo_min"],
                 "resumo": "Trajeto mais direto — pode passar por áreas sensíveis.",
                 "geometria": rapida["geometria"]},
            ]
            recomendada = "A" if prioridade == "segura" else "C" if prioridade == "rapida" else "A"
            return rotas, recomendada

        # n == 3
        outras = [r for r in enriched if r is not segura and r is not rapida]
        equilibrada = outras[0] if outras else by_time[len(by_time) // 2]
        rotas = [
            {"id": "A", "label": "Mais segura", "cor": "#10B981",
             "score_risco": segura["score"],
             "distancia_km": segura["distancia_km"], "tempo_min": segura["tempo_min"],
             "resumo": f"Evita áreas com mais ocorrências (pior trecho: {segura['bairro_pior']}).",
             "geometria": segura["geometria"]},
            {"id": "B", "label": "Equilibrada", "cor": "#3B82F6",
             "score_risco": equilibrada["score"],
             "distancia_km": equilibrada["distancia_km"], "tempo_min": equilibrada["tempo_min"],
             "resumo": "Bom compromisso entre segurança e tempo.",
             "geometria": equilibrada["geometria"]},
            {"id": "C", "label": "Mais rápida", "cor": "#F97316",
             "score_risco": rapida["score"],
             "distancia_km": rapida["distancia_km"], "tempo_min": rapida["tempo_min"],
             "resumo": "Trajeto mais direto — pode atravessar áreas sensíveis.",
             "geometria": rapida["geometria"]},
        ]
        recomendada = {"segura": "A", "rapida": "C"}.get(prioridade, "B")
        return rotas, recomendada

    def _rotas_fallback(self, o, d, origem, destino, modo, prioridade, horario_iso,
                        hora, bairro_o, bairro_d, dist_km):
        """Fallback didático quando Mapbox Directions não responde."""
        velocidade = {"carro": 30, "transporte_publico": 20, "bicicleta": 15, "ape": 5}.get(modo, 15)
        tempo_min = max(1, round(dist_km / velocidade * 60))
        risco = (self.calcular_risco(bairro_o, hora, modo) +
                 self.calcular_risco(bairro_d, hora, modo)) / 2

        def linha(off_lat, off_lon):
            mid = ((o[0] + d[0]) / 2 + off_lat, (o[1] + d[1]) / 2 + off_lon)
            return [[o[1], o[0]], [mid[1], mid[0]], [d[1], d[0]]]

        rotas = [
            {"id": "A", "label": "Mais segura", "cor": "#10B981",
             "score_risco": round(max(0.5, risco - 1.5), 2),
             "distancia_km": round(dist_km * 1.15, 2), "tempo_min": round(tempo_min * 1.2),
             "resumo": "⚠️ Modo offline (sem Mapbox Directions). Estimativa aproximada.",
             "geometria": linha(0.005, -0.005)},
            {"id": "B", "label": "Equilibrada", "cor": "#3B82F6",
             "score_risco": round(risco, 2),
             "distancia_km": round(dist_km * 1.05, 2), "tempo_min": round(tempo_min * 1.05),
             "resumo": "⚠️ Modo offline. Configure MAPBOX_TOKEN para rotas reais.",
             "geometria": linha(0, 0)},
            {"id": "C", "label": "Mais rápida", "cor": "#F97316",
             "score_risco": round(min(10.0, risco + 1.5), 2),
             "distancia_km": round(dist_km, 2), "tempo_min": tempo_min,
             "resumo": "⚠️ Modo offline. Linha reta entre origem e destino.",
             "geometria": linha(-0.005, 0.005)},
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
            "modo_offline": True,
        }

    def _nearest_bairro(self, lat: float, lon: float) -> str:
        best, best_d = None, 1e9
        for bairro, (clat, clon) in self.loader._centroides.items():
            d = _haversine_km(lat, lon, clat, clon)
            if d < best_d:
                best_d, best = d, bairro
        return best or "Sé"

    # ──────────────────────────────────────────────────────────────────
    def get_map_geojson(self, filter_type: str = "all") -> dict:
        return self.loader.geojson(filter_type)

    def compartilhar(self, payload: dict) -> str:
        token = secrets.token_urlsafe(8)
        _SHARED_ROUTES[token] = {"payload": payload, "ts": int(time.time())}
        return token

    def recuperar_compartilhada(self, token: str) -> Optional[dict]:
        entry = _SHARED_ROUTES.get(token)
        return entry["payload"] if entry else None
