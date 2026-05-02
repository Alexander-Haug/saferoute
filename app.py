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
    app.register_blueprint(auth_bp)  # /login, /registro, /perfil, /api/favoritas

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
