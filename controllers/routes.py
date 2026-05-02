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


@api_bp.route("/compartilhar-rota", methods=["POST"])
def api_compartilhar_rota():
    payload = request.get_json(force=True, silent=True) or {}
    token = SafeRouteFacade().compartilhar(payload)
    return jsonify({"id": token, "url": f"/compartilhado?id={token}"})
