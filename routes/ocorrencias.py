from flask import Blueprint, request, jsonify, flash, redirect, url_for
from database.db import get_db

ocorrencias_bp = Blueprint("ocorrencias", __name__)

TIPOS_VALIDOS = [
    "Assalto / Roubo",
    "Furto",
    "Iluminação precária",
    "Suspeito / Movimento estranho",
    "Acidente",
    "Outro",
]


@ocorrencias_bp.route("/reportar", methods=["POST"])
def reportar():
    """Salva uma ocorrência reportada pelo usuário no banco de dados."""
    tipo      = request.form.get("tipo", "").strip()
    descricao = request.form.get("descricao", "").strip()
    lat       = request.form.get("latitude",  type=float)
    lon       = request.form.get("longitude", type=float)

    if not tipo or tipo not in TIPOS_VALIDOS:
        flash("Selecione um tipo de ocorrência válido.", "error")
        return redirect(url_for("mapa.index"))

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO ocorrencias (tipo, latitude, longitude, descricao) VALUES (?, ?, ?, ?)",
            (tipo, lat, lon, descricao or None),
        )
        conn.commit()
        conn.close()
        flash("Ocorrência registrada. Obrigado por contribuir com a comunidade!", "success")
    except Exception as e:
        flash(f"Erro ao salvar ocorrência: {e}", "error")

    return redirect(url_for("mapa.index"))


@ocorrencias_bp.route("/api/ocorrencias-recentes")
def ocorrencias_recentes():
    """Retorna as últimas 50 ocorrências reportadas (usadas no heatmap)."""
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT tipo, latitude, longitude, criado_em FROM ocorrencias "
            "WHERE latitude IS NOT NULL ORDER BY criado_em DESC LIMIT 50"
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception:
        return jsonify([])
