"""
Camada SQLAlchemy: User, RotaFavorita, HistoricoBusca, PreferenciasUsuario.

# MELH v2: Caminho B — auth básica com SQLite + bcrypt + Flask-Login.
Sem JWT/refresh tokens (escolha consciente: fora do escopo desta sessão).
"""
from __future__ import annotations
import uuid
from datetime import datetime
import bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin


db = SQLAlchemy()


def _uuid() -> str:
    return str(uuid.uuid4())


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    nome_completo = db.Column(db.String(255), nullable=False)
    foto_perfil_url = db.Column(db.String(500))
    tema = db.Column(db.String(10), default="claro")  # claro | escuro
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)
    ativo = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False, index=True)

    favoritas = db.relationship("RotaFavorita", backref="user", cascade="all, delete-orphan")
    historico = db.relationship("HistoricoBusca", backref="user", cascade="all, delete-orphan")

    # ---- bcrypt helpers ----
    def set_password(self, senha: str) -> None:
        self.senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode()

    def check_password(self, senha: str) -> bool:
        try:
            return bcrypt.checkpw(senha.encode("utf-8"), self.senha_hash.encode("utf-8"))
        except Exception:
            return False

    @property
    def is_active(self) -> bool:  # Flask-Login
        return bool(self.ativo)


class RotaFavorita(db.Model):
    __tablename__ = "rotas_favoritas"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), index=True)
    origem = db.Column(db.Text, nullable=False)
    destino = db.Column(db.Text, nullable=False)
    modo_transporte = db.Column(db.String(40), default="ape")
    prioridade = db.Column(db.String(20), default="equilibrada")
    nome_personalizado = db.Column(db.String(255))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "origem": self.origem,
            "destino": self.destino,
            "modo": self.modo_transporte,
            "prioridade": self.prioridade,
            "nome": self.nome_personalizado or f"{self.origem} → {self.destino}",
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }


class HistoricoBusca(db.Model):
    __tablename__ = "historico_buscas"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), index=True)
    origem = db.Column(db.Text, nullable=False)
    destino = db.Column(db.Text, nullable=False)
    modo_transporte = db.Column(db.String(40))
    prioridade = db.Column(db.String(20))
    score_risco = db.Column(db.Float)
    tempo_min = db.Column(db.Integer)
    data_busca = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "origem": self.origem,
            "destino": self.destino,
            "modo": self.modo_transporte,
            "prioridade": self.prioridade,
            "score_risco": self.score_risco,
            "tempo_min": self.tempo_min,
            "data_busca": self.data_busca.isoformat() if self.data_busca else None,
        }


class Report(db.Model):
    """Reporte de ocorrência feito por usuário (Feature 11)."""
    __tablename__ = "reports"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    tipo = db.Column(db.String(40), nullable=False)
    descricao = db.Column(db.Text)
    endereco = db.Column(db.Text)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    quando = db.Column(db.DateTime)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    moderado = db.Column(db.Boolean, default=False)

    user = db.relationship("User", backref="reports")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "descricao": self.descricao,
            "endereco": self.endereco,
            "lat": self.lat, "lon": self.lon,
            "quando": self.quando.isoformat() if self.quando else None,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "moderado": self.moderado,
        }


def init_db(app):
    """Cria tabelas se não existirem + auto-migração leve de colunas novas
    (is_admin, ultimo_login) sem precisar de Alembic."""
    from sqlalchemy import inspect, text
    with app.app_context():
        db.create_all()
        # Auto-migração: adiciona colunas que ainda não existem em bancos antigos
        try:
            insp = inspect(db.engine)
            cols = {c["name"] for c in insp.get_columns("users")}
            with db.engine.begin() as conn:
                if "is_admin" not in cols:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL"
                    ))
                if "ultimo_login" not in cols:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN ultimo_login TIMESTAMP"
                    ))
        except Exception as e:
            # Em produção (Postgres) o "DEFAULT 0" pode falhar — usa FALSE
            try:
                with db.engine.begin() as conn:
                    if "is_admin" not in cols:
                        conn.execute(text(
                            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL"
                        ))
            except Exception:
                pass
