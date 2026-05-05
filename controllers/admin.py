"""
Painel administrativo — protegido por @admin_required (is_admin=True no banco).

Rotas:
  /admin                 → redireciona pra /admin/users
  /admin/users           → lista todos os usuários
  /admin/users/<id>      → detalhes de um usuário
  /admin/analytics       → telemetria agregada
"""
from functools import wraps
from flask import Blueprint, render_template, abort, redirect, url_for, request, flash
from flask_login import current_user, login_required

from models.analytics import Analytics
from models.db import db, User, RotaFavorita, HistoricoBusca, Report


admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """Bloqueia acesso a quem não é is_admin. Retorna 403."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/")
@login_required
@admin_required
def admin_index():
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/users")
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.criado_em.desc()).all()

    # Conta rotas e favoritas por usuário (uma query, evita N+1)
    rotas_por_user = dict(
        db.session.query(HistoricoBusca.user_id, db.func.count(HistoricoBusca.id))
        .group_by(HistoricoBusca.user_id).all()
    )
    favs_por_user = dict(
        db.session.query(RotaFavorita.user_id, db.func.count(RotaFavorita.id))
        .group_by(RotaFavorita.user_id).all()
    )

    rows = []
    for u in users:
        rows.append({
            "id": u.id,
            "email": u.email,
            "nome": u.nome_completo,
            "criado_em": u.criado_em,
            "ultimo_login": u.ultimo_login,
            "ativo": u.ativo,
            "is_admin": u.is_admin,
            "n_rotas": rotas_por_user.get(u.id, 0),
            "n_favs": favs_por_user.get(u.id, 0),
        })

    # Estatísticas gerais
    stats = {
        "total_users": len(users),
        "ativos": sum(1 for u in users if u.ativo),
        "admins": sum(1 for u in users if u.is_admin),
        "total_rotas": HistoricoBusca.query.count(),
        "total_reportes": Report.query.count(),
        "total_favoritas": RotaFavorita.query.count(),
    }
    return render_template("admin_users.html", users=rows, stats=stats)


@admin_bp.route("/users/<user_id>")
@login_required
@admin_required
def admin_user_detail(user_id):
    user = User.query.get_or_404(user_id)
    historico = HistoricoBusca.query.filter_by(user_id=user.id) \
        .order_by(HistoricoBusca.data_busca.desc()).limit(50).all()
    favoritas = RotaFavorita.query.filter_by(user_id=user.id) \
        .order_by(RotaFavorita.criado_em.desc()).all()
    reportes = Report.query.filter_by(user_id=user.id) \
        .order_by(Report.criado_em.desc()).limit(20).all()
    return render_template("admin_user_detail.html",
                           user=user,
                           historico=[h.to_dict() for h in historico],
                           favoritas=[f.to_dict() for f in favoritas],
                           reportes=[r.to_dict() for r in reportes])


@admin_bp.route("/users/<user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
def admin_toggle_admin(user_id):
    """Promove/rebaixa user. Não permite que admin remova a si mesmo (anti-lockout)."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Você não pode remover seu próprio admin (anti-lockout).", "error")
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        flash(f"{user.email} agora é {'admin' if user.is_admin else 'usuário comum'}.", "success")
    return redirect(url_for("admin.admin_user_detail", user_id=user.id))


@admin_bp.route("/users/<user_id>/toggle-ativo", methods=["POST"])
@login_required
@admin_required
def admin_toggle_ativo(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Você não pode desativar a si mesmo.", "error")
    else:
        user.ativo = not user.ativo
        db.session.commit()
        flash(f"{user.email} {'ativado' if user.ativo else 'desativado'}.", "success")
    return redirect(url_for("admin.admin_user_detail", user_id=user.id))


@admin_bp.route("/analytics")
@login_required
@admin_required
def admin_analytics():
    data = Analytics.instance().get_dashboard_data()
    return render_template("admin_analytics.html", data=data)
