import json
import os
import requests as req
from flask import Blueprint, render_template, request, jsonify
from models.gerenciador_dados import GerenciadorDeDados, CATEGORIAS

mapa_bp = Blueprint("mapa", __name__)

_ROADS_CACHE   = os.path.join("dados", "sp_rodovias.json")
_OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
_OVERPASS_QUERY = """
[out:json][timeout:120];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]
    (-23.82,-46.92,-23.38,-46.28);
);
out geom;
"""
_HIGHWAY_LARGURA = {
    "motorway": 6, "trunk": 5, "primary": 4,
    "secondary": 3, "tertiary": 2,
}


def _baixar_rodovias() -> list:
    if os.path.exists(_ROADS_CACHE):
        with open(_ROADS_CACHE, encoding="utf-8") as f:
            return json.load(f).get("elements", [])
    print("[Mapa] Baixando vias do Overpass (1ª vez, ~60 s)…")
    for url in _OVERPASS_URLS:
        try:
            resp = req.post(url, data={"data": _OVERPASS_QUERY},
                            timeout=120, headers={"User-Agent": "SafeRoute/1.0"})
            resp.raise_for_status()
            data = resp.json()
            os.makedirs("dados", exist_ok=True)
            with open(_ROADS_CACHE, "w", encoding="utf-8") as f:
                json.dump(data, f)
            print(f"[Mapa] {len(data.get('elements',[]))} vias salvas em cache.")
            return data.get("elements", [])
        except Exception as e:
            print(f"[Mapa] {url} falhou: {e}")
    return []


def _criar_grid(df, tamanho: float = 0.005) -> dict:
    if df.empty:
        return {}
    d = df.copy()
    d["li"] = (d["latitude"]  / tamanho).astype(int)
    d["lo"] = (d["longitude"] / tamanho).astype(int)
    return d.groupby(["li", "lo"])["score_risco"].mean().to_dict()


def _score_no_grid(lat, lon, grid, tamanho=0.005) -> float:
    li, lo = int(lat / tamanho), int(lon / tamanho)
    scores = [grid[k] for dla in range(-2, 3) for dlo in range(-2, 3)
              if (k := (li + dla, lo + dlo)) in grid]
    return sum(scores) / len(scores) if scores else -1.0


def _gerar_geojson_vias(df) -> dict:
    rodovias = _baixar_rodovias()
    grid     = _criar_grid(df)
    features = []
    for elem in rodovias:
        if elem.get("type") != "way" or not elem.get("geometry"):
            continue
        geom  = elem["geometry"]
        passo = max(1, len(geom) // 30)
        coords = [[n["lon"], n["lat"]] for n in geom[::passo]]
        if len(coords) < 2:
            continue
        mid   = geom[len(geom) // 2]
        score = _score_no_grid(mid["lat"], mid["lon"], grid)
        tipo  = elem.get("tags", {}).get("highway", "tertiary")
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "score":   round(score, 3),
                "highway": tipo,
                "largura": _HIGHWAY_LARGURA.get(tipo, 2),
            },
        })
    return {"type": "FeatureCollection", "features": features}


@mapa_bp.route("/")
def index():
    gerenciador = GerenciadorDeDados()
    return render_template("index.html", stats=gerenciador.obter_stats())


@mapa_bp.route("/api/rodovias")
def api_rodovias():
    categoria    = request.args.get("categoria", "todos")
    tipos_filtro = CATEGORIAS.get(categoria)
    gerenciador  = GerenciadorDeDados()
    df = gerenciador.obter_dados().copy()
    if tipos_filtro:
        df = df[df["tipo_crime"].isin(tipos_filtro)]
    elif categoria == "seguras":
        df = df[df["score_risco"] < 0.25]
    return jsonify(_gerar_geojson_vias(df))


@mapa_bp.route("/api/verificar-risco")
def api_verificar_risco():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"score": 0, "nivel": "Desconhecido", "cor": "#888"})
    df    = GerenciadorDeDados().obter_dados()
    delta = 0.4 / 111
    viz   = df[df["latitude"].between(lat - delta, lat + delta) &
               df["longitude"].between(lon - delta, lon + delta)]
    score = float(viz["score_risco"].mean()) if not viz.empty else 0.0
    if score < 0.15:   nivel, cor = "Baixo",   "#27ae60"
    elif score < 0.35: nivel, cor = "Médio",   "#f39c12"
    elif score < 0.6:  nivel, cor = "Alto",    "#e67e22"
    else:              nivel, cor = "Crítico", "#e74c3c"
    return jsonify({"score": round(score * 100), "nivel": nivel, "cor": cor})
