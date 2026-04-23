"""
Gera o mapa de risco de São Paulo: ruas do OSMnx coloridas por score de crime.

Fluxo:
  1. Baixa grafo viário via OSMnx (1ª vez, ~5-15 min) → cache em GPKG
  2. Atribui score de risco a cada segmento via pandas merge com grid de crimes
  3. Gera HTML Folium com GeoJson único + legenda
  4. Cacheia o HTML por categoria para requests subsequentes serem instantâneos
"""

import json
import os
import threading

import folium
import geopandas as gpd
import pandas as pd
from folium.plugins import HeatMap

from models.gerenciador_dados import CATEGORIAS

# ── Caminhos de cache ─────────────────────────────────────────────────────────
_DIR         = "dados"
_CACHE_GDF   = os.path.join(_DIR, "sp_ruas.gpkg")
_CACHE_HTML  = {
    cat: os.path.join(_DIR, f"mapa_{cat}.html")
    for cat in ("todos", "roubos_furtos", "homicidios", "seguras")
}

# Bounding box de SP (cobre os 30 bairros do dataset)
_BBOX = dict(north=-23.40, south=-23.72, east=-46.30, west=-46.85)

# Estado da geração em background
_gerando = False


# ── Paleta de cores ───────────────────────────────────────────────────────────

def _cor(score: float) -> str:
    if score < 0:    return "#9e9e9e"   # cinza   — sem dados
    if score < 0.20: return "#6b9e78"   # verde   — baixo
    if score < 0.45: return "#e9c46a"   # amarelo — médio
    if score < 0.70: return "#f4a261"   # laranja — médio-alto
    return "#e63946"                    # vermelho — alto


def _nivel(score: float) -> str:
    if score < 0:    return "Sem dados"
    if score < 0.20: return "Baixo"
    if score < 0.45: return "Médio"
    if score < 0.70: return "Médio-alto"
    return "Alto"


# ── Download OSMnx ────────────────────────────────────────────────────────────

def _baixar_ruas() -> gpd.GeoDataFrame:
    """Retorna GeoDataFrame das vias de SP (baixa e cacheia se necessário)."""
    if os.path.exists(_CACHE_GDF):
        print("[Mapa] Carregando ruas do cache local...")
        return gpd.read_file(_CACHE_GDF)

    try:
        import osmnx as ox
    except ImportError:
        raise RuntimeError(
            "OSMnx não instalado. Execute no terminal (venv ativado):\n"
            "  pip install osmnx"
        )

    print("[Mapa] Baixando rede viária de SP via OSMnx...")
    print("[Mapa] Isso pode levar 5-15 minutos na primeira execução.")

    G = ox.graph_from_bbox(
        north=_BBOX["north"], south=_BBOX["south"],
        east=_BBOX["east"],  west=_BBOX["west"],
        network_type="drive",
        simplify=True,
    )

    gdf = ox.graph_to_gdfs(G, nodes=False).reset_index()

    # Mantém apenas colunas necessárias
    cols_manter = ["geometry"] + [
        c for c in ("name", "highway", "length") if c in gdf.columns
    ]
    gdf = gdf[cols_manter].to_crs("EPSG:4326")

    os.makedirs(_DIR, exist_ok=True)
    gdf.to_file(_CACHE_GDF, driver="GPKG")
    print(f"[Mapa] {len(gdf):,} segmentos salvos em cache ({_CACHE_GDF})")
    return gdf


# ── Atribuição de scores ──────────────────────────────────────────────────────

def _atribuir_scores(gdf: gpd.GeoDataFrame, df_crimes: pd.DataFrame,
                     tamanho: float = 0.005) -> gpd.GeoDataFrame:
    """
    Cruza cada segmento de rua com o grid de crimes via pandas merge.
    Vetorizado — não usa loops Python sobre os segmentos.
    """
    gdf = gdf.copy()

    if df_crimes.empty:
        gdf["score"] = -1.0
        return gdf

    # Monta grid: célula → score médio
    dc = df_crimes.copy()
    dc["li"] = (dc["latitude"]  / tamanho).astype(int)
    dc["lo"] = (dc["longitude"] / tamanho).astype(int)
    grid = (
        dc.groupby(["li", "lo"])["score_risco"]
        .mean()
        .reset_index()
        .rename(columns={"score_risco": "score"})
    )

    # Centroide de cada segmento → qual célula do grid
    c = gdf.geometry.centroid
    gdf["li"] = (c.y / tamanho).astype(int)
    gdf["lo"] = (c.x / tamanho).astype(int)

    # Merge: segmento + score da célula correspondente
    gdf = gdf.merge(grid, on=["li", "lo"], how="left")
    gdf["score"] = gdf["score"].fillna(-1.0)
    return gdf


# ── Geração do HTML Folium ────────────────────────────────────────────────────

def _gerar_html(gdf: gpd.GeoDataFrame) -> str:
    """Gera mapa Folium com ruas coloridas por risco. Retorna HTML."""

    mapa = folium.Map(
        location=[-23.55, -46.63],
        zoom_start=12,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    # Prepara colunas de estilo e tooltip
    gdf = gdf.copy()
    gdf["cor"]   = gdf["score"].apply(_cor)
    gdf["nivel"] = gdf["score"].apply(_nivel)
    gdf["rua"]   = (
        gdf.get("name", pd.Series(["Sem nome"] * len(gdf)))
        .fillna("Sem nome")
        .astype(str)
        .str[:60]
    )

    # Simplifica geometria → reduz tamanho do HTML gerado
    gdf["geometry"] = gdf["geometry"].simplify(0.00005)

    geojson = json.loads(
        gdf[["geometry", "cor", "nivel", "rua"]].to_json()
    )

    folium.GeoJson(
        geojson,
        name="vias_risco",
        style_function=lambda f: {
            "color":   f["properties"]["cor"],
            "weight":  1.5,
            "opacity": 0.85,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["rua", "nivel"],
            aliases=["Rua:", "Risco:"],
            sticky=True,
            style="font-size:12px;",
        ),
    ).add_to(mapa)

    # Legenda fixa no canto inferior esquerdo
    legenda = """
    <div style="position:fixed;bottom:24px;left:24px;z-index:9999;
                background:rgba(10,10,10,0.82);color:#eee;
                padding:10px 16px;border-radius:8px;font-size:12px;
                line-height:2.1;border:1px solid rgba(255,255,255,0.1)">
      <b style="font-size:13px">Nível de Risco</b><br>
      <span style="color:#e63946;font-size:18px">&#9644;</span>&nbsp;Alto risco<br>
      <span style="color:#f4a261;font-size:18px">&#9644;</span>&nbsp;Médio-alto<br>
      <span style="color:#e9c46a;font-size:18px">&#9644;</span>&nbsp;Médio<br>
      <span style="color:#6b9e78;font-size:18px">&#9644;</span>&nbsp;Baixo risco<br>
      <span style="color:#9e9e9e;font-size:18px">&#9644;</span>&nbsp;Sem dados
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(legenda))

    return mapa._repr_html_()


def _gerar_fallback(df_crimes: pd.DataFrame) -> str:
    """HeatMap rápido servido enquanto o mapa OSMnx está sendo gerado."""
    mapa = folium.Map(
        location=[-23.55, -46.63],
        zoom_start=11,
        tiles="CartoDB dark_matter",
    )
    pontos = (
        df_crimes[["latitude", "longitude", "score_risco"]]
        .dropna()
        .values
        .tolist()
    )
    if pontos:
        HeatMap(
            pontos,
            min_opacity=0.4,
            radius=10,
            blur=12,
            gradient={0.0: "#6b9e78", 0.4: "#e9c46a", 0.7: "#f4a261", 1.0: "#e63946"},
        ).add_to(mapa)
    return mapa._repr_html_()


# ── API pública ───────────────────────────────────────────────────────────────

def obter_mapa(df_crimes: pd.DataFrame, categoria: str = "todos") -> tuple:
    """
    Retorna (html, gerando_em_background).

    Se o cache existir → retorna o HTML cacheado (rápido).
    Se não existir    → retorna fallback e dispara geração em background.
    """
    global _gerando

    cache_path = _CACHE_HTML.get(categoria, _CACHE_HTML["todos"])

    # Cache hit → serve instantaneamente
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return f.read(), False

    # Cache miss → serve fallback e gera em background
    fallback = _gerar_fallback(df_crimes)

    if not _gerando:
        _gerando = True
        threading.Thread(
            target=_gerar_e_cachear,
            args=(df_crimes,),
            daemon=True,
        ).start()

    return fallback, True


def _gerar_e_cachear(df_crimes: pd.DataFrame):
    """
    Executa em background thread:
    Baixa OSMnx, atribui scores e gera os 4 HTMLs cacheados.
    """
    global _gerando
    try:
        gdf_base = _baixar_ruas()

        for cat, cache_path in _CACHE_HTML.items():
            if os.path.exists(cache_path):
                continue  # já gerado

            df_cat = df_crimes.copy()
            tipos = CATEGORIAS.get(cat)
            if tipos:
                df_cat = df_cat[df_cat["tipo_crime"].isin(tipos)]
            elif cat == "seguras":
                df_cat = df_cat[df_cat["score_risco"] < 0.25]

            gdf = _atribuir_scores(gdf_base, df_cat)

            print(f"[Mapa] Gerando HTML '{cat}'...")
            html = _gerar_html(gdf)

            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[Mapa] '{cat}' salvo → {cache_path}")

    except Exception as e:
        print(f"[Mapa] Erro na geração em background: {e}")
    finally:
        _gerando = False
