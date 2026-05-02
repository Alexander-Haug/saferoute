"""
Reportar ocorrência — Feature 11.

Pede login (anti-spam). POST cria registro pendente de moderação.
GET lista os 20 reportes mais recentes do próprio usuário.
"""
from __future__ import annotations
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from models.db import db, Report


reports_bp = Blueprint("reports", __name__)

TIPOS_VALIDOS = {
    "iluminacao_ruim": "💡 Iluminação ruim",
    "calcada_quebrada": "🚧 Calçada/via em mau estado",
    "sensacao_inseguranca": "😟 Sensação de insegurança",
    "roubo_furto": "🚨 Roubo / furto presenciado",
    "acidente": "💥 Acidente",
    "ponto_seguro": "✅ Ponto seguro / bem iluminado",
    "outro": "❔ Outro",
}


@reports_bp.route("/reportar", methods=["GET", "POST"])
@login_required
def reportar():
    if request.method == "POST":
        tipo = request.form.get("tipo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        endereco = request.form.get("endereco", "").strip()
        lat = request.form.get("lat", "")
        lon = request.form.get("lon", "")
        quando_str = request.form.get("quando", "")

        if tipo not in TIPOS_VALIDOS:
            flash("Tipo de ocorrência inválido.", "error")
        elif len(endereco) < 5:
            flash("Informe um endereço (mín. 5 caracteres).", "error")
        else:
            try:
                lat_f = float(lat) if lat else None
                lon_f = float(lon) if lon else None
            except ValueError:
                lat_f = lon_f = None
            quando = None
            try:
                if quando_str:
                    quando = datetime.fromisoformat(quando_str)
            except ValueError:
                pass

            r = Report(
                user_id=current_user.id, tipo=tipo,
                descricao=descricao, endereco=endereco,
                lat=lat_f, lon=lon_f, quando=quando,
            )
            db.session.add(r)
            db.session.commit()
            flash("✅ Reporte enviado. Obrigado por ajudar a comunidade!", "success")
            return redirect(url_for("reports.reportar"))

    meus = Report.query.filter_by(user_id=current_user.id) \
        .order_by(Report.criado_em.desc()).limit(20).all()
    return render_template("reportar.html",
                           tipos=TIPOS_VALIDOS,
                           meus=[r.to_dict() for r in meus])


@reports_bp.route("/api/reportes/<rid>", methods=["DELETE"])
@login_required
def api_apagar_reporte(rid):
    r = Report.query.filter_by(id=rid, user_id=current_user.id).first()
    if not r:
        return jsonify({"erro": "não encontrada"}), 404
    db.session.delete(r)
    db.session.commit()
    return jsonify({"ok": True})
