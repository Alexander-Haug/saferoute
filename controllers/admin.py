"""
Dashboard administrativo — Tarefa 4.6.
Mostra métricas agregadas de uso, sem nenhum dado pessoal.
"""
from flask import Blueprint, render_template
from models.analytics import Analytics


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/analytics")
def admin_analytics():
    data = Analytics.instance().get_dashboard_data()
    return render_template("admin_analytics.html", data=data)
