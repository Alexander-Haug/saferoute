"""
Endpoints HTTP — páginas e API REST.

# MELH v2: histórico vai pro DB quando o usuário está logado;
# convidados continuam usando localStorage.
"""
from __future__ import annotations
import json
import os
import time
from datetime import datetime
import pytz

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import current_user

from flask_login import login_required
from services.facade import SafeRouteFacade
from models.analytics import Analytics
from models.db import db, HistoricoBusca


api_bp = Blueprint("api", __name__)
TZ = pytz.timezone("America/Sao_Paulo")


def register_pages(app):
    """Registra rotas HTML diretamente no app."""

    @app.route("/")
    def landing():
        return render_template("landing.html")

    @app.route("/app")
    def mapa():
        return render_template("app.html",
                               agora=datetime.now(TZ).strftime("%Y-%m-%dT%H:%M"))

    # Bug 7 — redirects de URLs antigas
    @app.route("/mapa")
    def mapa_legacy():
        return redirect(url_for("mapa"), code=301)

    @app.route("/buscar")
    def buscar_legacy():
        return redirect(url_for("mapa") + "#search", code=301)

    @app.route("/app/rota/resultado")
    def resultado_rota():
        origem = request.args.get("origem", "")
        destino = request.args.get("destino", "")
        horario = request.args.get("horario", datetime.now(TZ).isoformat())
        prioridade = request.args.get("prioridade", "equilibrada")
        modo = request.args.get("modo", "ape")

        t0 = time.time()
        facade = SafeRouteFacade()
        dados = facade.get_route_details(origem, destino, horario, prioridade, modo)
        elapsed = int((time.time() - t0) * 1000)

        sucesso = dados.get("erro") is None
        bairro = dados.get("destino", {}).get("bairro", "") if sucesso else ""
        Analytics.instance().log_busca(
            tipo_rota=prioridade, modo=modo,
            geocod_ok=sucesso, tempo_ms=elapsed,
            bairro=bairro, sucesso=sucesso,
        )

        # Histórico no DB se o usuário estiver logado
        if sucesso and current_user.is_authenticated:
            recomendada = next((r for r in dados["rotas"] if r["id"] == dados["recomendada"]), dados["rotas"][1])
            h = HistoricoBusca(
                user_id=current_user.id,
                origem=origem, destino=destino,
                modo_transporte=modo, prioridade=prioridade,
                score_risco=recomendada["score_risco"],
                tempo_min=recomendada["tempo_min"],
            )
            db.session.add(h)
            db.session.commit()

        return render_template("rota_resultado.html", dados=dados, elapsed_ms=elapsed)

    @app.route("/compartilhado")
    def compartilhado():
        token = request.args.get("id", "")
        facade = SafeRouteFacade()
        payload = facade.recuperar_compartilhada(token)
        if not payload:
            return render_template("app.html",
                                   agora=datetime.now(TZ).strftime("%Y-%m-%dT%H:%M"),
                                   erro_compartilhamento="Link expirado ou inválido.")
        return redirect(url_for("resultado_rota", **payload))

    @app.route("/historico")
    def historico():
        # Se logado, pega do DB; senão, render vazio (JS preenche do localStorage).
        items = []
        if current_user.is_authenticated:
            items = [h.to_dict() for h in HistoricoBusca.query
                     .filter_by(user_id=current_user.id)
                     .order_by(HistoricoBusca.data_busca.desc()).limit(50).all()]
        return render_template("historico.html", items=items, logado=current_user.is_authenticated)


# ---------------------------------------------------------------------------
# API JSON
# ---------------------------------------------------------------------------
@api_bp.route("/info", methods=["GET"])
def api_info():
    meta_path = os.path.join("data", "metadata.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@api_bp.route("/suggest", methods=["GET"])
def api_suggest():
    """Autocomplete de endereços. Usado pelo frontend nos campos origem/destino."""
    q = request.args.get("q", "")
    return jsonify(SafeRouteFacade().suggest(q))


@api_bp.route("/reverse-geocode", methods=["GET"])
def api_reverse_geocode():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"erro": "lat/lon inválidos"}), 400
    addr = SafeRouteFacade().reverse_geocode(lat, lon)
    return jsonify({"endereco": addr, "lat": lat, "lon": lon})


@api_bp.route("/map-data", methods=["GET"])
def api_map_data():
    filtro = request.args.get("filter", "all")
    return jsonify(SafeRouteFacade().get_map_geojson(filtro))


@api_bp.route("/buscar-rota", methods=["POST"])
def api_buscar_rota():
    payload = request.get_json(force=True, silent=True) or {}
    facade = SafeRouteFacade()
    t0 = time.time()
    dados = facade.get_route_details(
        origem=payload.get("origem", ""),
        destino=payload.get("destino", ""),
        horario_iso=payload.get("horario", datetime.now(TZ).isoformat()),
        prioridade=payload.get("prioridade", "equilibrada"),
        modo=payload.get("modo", "ape"),
    )
    elapsed = int((time.time() - t0) * 1000)
    sucesso = dados.get("erro") is None
    Analytics.instance().log_busca(
        tipo_rota=payload.get("prioridade", "equilibrada"),
        modo=payload.get("modo", "ape"),
        geocod_ok=sucesso, tempo_ms=elapsed,
        bairro=dados.get("destino", {}).get("bairro", "") if sucesso else "",
        sucesso=sucesso,
    )
    return jsonify(dados)


@api_bp.route("/speed-limit", methods=["GET"])
def api_speed_limit():
    """Retorna o maxspeed da via mais próxima do ponto (lat,lon).
    Item #2: usa OpenStreetMap Overpass (Mapbox cobra speed-limit)."""
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"erro": "lat/lon inválidos"}), 400

    # Bounding box pequena ao redor do ponto (~80m)
    delta = 0.0008
    bbox = f"{lat-delta},{lon-delta},{lat+delta},{lon+delta}"
    query = (
        f'[out:json][timeout:5];'
        f'way["highway"]["maxspeed"]({bbox});'
        f'out tags geom 1;'
    )
    import requests as _r
    try:
        r = _r.post("https://overpass-api.de/api/interpreter",
                    data=query, timeout=8,
                    headers={"User-Agent": "SafeRoute-PUC-SP/2.x"})
        if r.ok:
            els = r.json().get("elements", [])
            if els:
                # Pega o primeiro com maxspeed válido
                for e in els:
                    speed = e.get("tags", {}).get("maxspeed", "")
                    # OSM geralmente vem como "60" ou "60 km/h"
                    digits = "".join(c for c in speed if c.isdigit())
                    if digits:
                        return jsonify({
                            "limite": int(digits),
                            "via": e.get("tags", {}).get("name", ""),
                            "fonte": "OpenStreetMap",
                        })
        return jsonify({"limite": None, "via": "", "fonte": "OpenStreetMap"})
    except Exception:
        return jsonify({"limite": None, "via": "", "erro": "timeout"}), 504


@api_bp.route("/radares", methods=["GET"])
def api_radares():
    """Item #8: radares (speed cameras) ao longo de uma bbox.
    Frontend manda bbox = bounds da rota recomendada."""
    bbox = request.args.get("bbox", "")  # formato: lat1,lon1,lat2,lon2
    try:
        parts = [float(p) for p in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError
    except ValueError:
        return jsonify({"erro": "bbox inválido"}), 400
    s, w, n, e = parts
    query = (
        f'[out:json][timeout:8];'
        f'('
        f'  node["highway"="speed_camera"]({s},{w},{n},{e});'
        f'  node["enforcement"="maxspeed"]({s},{w},{n},{e});'
        f');'
        f'out body;'
    )
    import requests as _r
    try:
        r = _r.post("https://overpass-api.de/api/interpreter",
                    data=query, timeout=12,
                    headers={"User-Agent": "SafeRoute-PUC-SP/2.x"})
        if r.ok:
            radares = []
            for el in r.json().get("elements", []):
                if "lat" in el and "lon" in el:
                    radares.append({
                        "lat": el["lat"], "lon": el["lon"],
                        "limite": el.get("tags", {}).get("maxspeed", "?"),
                        "tipo": el.get("tags", {}).get("highway", "speed_camera"),
                    })
            return jsonify({"radares": radares, "fonte": "OpenStreetMap"})
        return jsonify({"radares": []})
    except Exception:
        return jsonify({"radares": [], "erro": "timeout"}), 504


@api_bp.route("/compartilhar-rota", methods=["POST"])
def api_compartilhar_rota():
    payload = request.get_json(force=True, silent=True) or {}
    token = SafeRouteFacade().compartilhar(payload)
    return jsonify({"id": token, "url": f"/compartilhado?id={token}"})


@api_bp.route("/historico/<hid>", methods=["DELETE"])
@login_required
def api_historico_delete(hid):
    """Apaga um item do histórico do usuário logado."""
    from flask_login import current_user
    h = HistoricoBusca.query.filter_by(id=hid, user_id=current_user.id).first()
    if not h:
        return jsonify({"erro": "não encontrada"}), 404
    db.session.delete(h)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/historico", methods=["DELETE"])
@login_required
def api_historico_clear():
    """Limpa TODO o histórico do usuário logado."""
    from flask_login import current_user
    HistoricoBusca.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"ok": True})
