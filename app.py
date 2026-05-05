"""
SafeRoute v2 — entry point Flask.
- Auth: SQLite + bcrypt + Flask-Login
- Mapa: Mapbox GL JS (token público via env)
- UI: visual app-like (bottom nav, dark mode, splash)
"""
from __future__ import annotations
import os
import json
from datetime import datetime
import pytz

from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv

from controllers.routes import api_bp, register_pages
from controllers.admin import admin_bp
from controllers.auth import auth_bp
from controllers.reports import reports_bp
from models.db import db, User, init_db
from models.data_loader import DataLoader
from models.geocoding_cache import GeocodeCache
from models.analytics import Analytics


load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Config
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///saferoute.db"
    ).replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAPBOX_TOKEN"] = os.environ.get("MAPBOX_TOKEN", "")

    # DB
    db.init_app(app)
    init_db(app)

    # Login manager
    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # Singletons (carregam dados em memória uma vez)
    DataLoader.instance()
    GeocodeCache.instance().purge_old()
    Analytics.instance().purge_old()

    # Páginas + blueprints
    register_pages(app)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(auth_bp)      # /login, /registro, /perfil, /api/favoritas
    app.register_blueprint(reports_bp)   # /reportar, /api/reportes

    # Variáveis disponíveis em todos os templates (footer, mapbox token, etc)
    @app.context_processor
    def inject_globals():
        meta_path = os.path.join("data", "metadata.json")
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {"version": "0.0.0", "ultima_atualizacao": "—"}
        return {
            "metadata": meta,
            "mapbox_token": app.config["MAPBOX_TOKEN"],
            "now_year": datetime.now(pytz.timezone("America/Sao_Paulo")).year,
        }

    return app


app = create_app()


# ─────────────────────────────────────────────────────────────────────
# CLI — comandos administrativos
#   Uso: flask make-admin email@dominio.com
#        flask list-users
# ─────────────────────────────────────────────────────────────────────
@app.cli.command("make-admin")
def make_admin_cmd():
    """Promove um usuário a admin (pede o email no terminal)."""
    import click
    email = click.prompt("Email do usuário a promover").strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        click.echo(f"❌ Usuário '{email}' não encontrado.")
        return
    user.is_admin = True
    db.session.commit()
    click.echo(f"✅ {email} agora é ADMIN. Acesse /admin após o login.")


@app.cli.command("list-users")
def list_users_cmd():
    """Lista todos os usuários cadastrados."""
    import click
    users = User.query.order_by(User.criado_em.desc()).all()
    if not users:
        click.echo("(nenhum usuário cadastrado)")
        return
    click.echo(f"Total: {len(users)} usuários")
    click.echo("-" * 80)
    for u in users:
        admin = "👑" if u.is_admin else "  "
        ativo = "✅" if u.ativo else "🚫"
        criado = u.criado_em.strftime("%d/%m/%Y") if u.criado_em else "—"
        click.echo(f"{admin} {ativo} {u.email:35s} {u.nome_completo:25s} {criado}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
