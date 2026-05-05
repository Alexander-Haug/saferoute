"""
Controller de autenticação — login, registro, perfil, logout.

# Caminho B: SQLite + bcrypt + Flask-Login (sem JWT, sem email).
"""
from __future__ import annotations
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from models.db import db, User, RotaFavorita, HistoricoBusca


auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[\w\.\+-]+@[\w-]+\.[\w\.-]+$")


def _validar_senha(senha: str) -> str | None:
    if len(senha) < 8:
        return "Senha precisa ter pelo menos 8 caracteres."
    if not re.search(r"[A-Z]", senha) or not re.search(r"[a-z]", senha):
        return "Senha precisa ter letra maiúscula e minúscula."
    if not re.search(r"\d", senha):
        return "Senha precisa ter pelo menos um número."
    return None


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("mapa"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        lembrar = request.form.get("lembrar") == "on"
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(senha):
            flash("E-mail ou senha incorretos.", "error")
            return render_template("auth/login.html", email=email)
        if not user.ativo:
            flash("Conta desativada.", "error")
            return render_template("auth/login.html", email=email)
        # Atualiza último login (rastreio admin)
        from datetime import datetime
        user.ultimo_login = datetime.utcnow()
        db.session.commit()
        login_user(user, remember=lembrar)
        return redirect(request.args.get("next") or url_for("mapa"))
    return render_template("auth/login.html")


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("mapa"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        nome = request.form.get("nome", "").strip()
        senha = request.form.get("senha", "")
        senha2 = request.form.get("senha_confirmacao", "")

        if not EMAIL_RE.match(email):
            flash("E-mail inválido.", "error")
        elif not nome or len(nome) < 2:
            flash("Informe seu nome completo.", "error")
        elif senha != senha2:
            flash("Senhas não coincidem.", "error")
        elif (msg := _validar_senha(senha)):
            flash(msg, "error")
        elif User.query.filter_by(email=email).first():
            flash("Já existe uma conta com este e-mail.", "error")
        else:
            user = User(email=email, nome_completo=nome)
            user.set_password(senha)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Conta criada com sucesso! Bem-vindo(a).", "success")
            return redirect(url_for("mapa"))

        return render_template("auth/register.html", email=email, nome=nome)
    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da conta.", "info")
    return redirect(url_for("landing"))


@auth_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        acao = request.form.get("acao")
        if acao == "dados":
            # Tema agora é controlado pelo toggle 🌓 do topbar (localStorage),
            # não vem mais do form do perfil.
            current_user.nome_completo = request.form.get("nome", "").strip() or current_user.nome_completo
            db.session.commit()
            flash("Dados atualizados.", "success")
        elif acao == "senha":
            atual = request.form.get("senha_atual", "")
            nova = request.form.get("nova_senha", "")
            nova2 = request.form.get("nova_senha2", "")
            if not current_user.check_password(atual):
                flash("Senha atual incorreta.", "error")
            elif nova != nova2:
                flash("As novas senhas não coincidem.", "error")
            elif (msg := _validar_senha(nova)):
                flash(msg, "error")
            else:
                current_user.set_password(nova)
                db.session.commit()
                flash("Senha alterada com sucesso.", "success")
        elif acao == "deletar":
            # soft delete
            current_user.ativo = False
            db.session.commit()
            logout_user()
            flash("Sua conta foi desativada.", "info")
            return redirect(url_for("landing"))
        return redirect(url_for("auth.perfil"))

    favoritas = RotaFavorita.query.filter_by(user_id=current_user.id) \
        .order_by(RotaFavorita.criado_em.desc()).all()
    historico = HistoricoBusca.query.filter_by(user_id=current_user.id) \
        .order_by(HistoricoBusca.data_busca.desc()).limit(20).all()
    return render_template(
        "perfil.html",
        favoritas=[f.to_dict() for f in favoritas],
        historico=[h.to_dict() for h in historico],
    )


# ---------------------------------------------------------------------------
# API JSON — favoritas
# ---------------------------------------------------------------------------
@auth_bp.route("/api/favoritas", methods=["GET", "POST"])
@login_required
def api_favoritas():
    if request.method == "GET":
        rows = RotaFavorita.query.filter_by(user_id=current_user.id) \
            .order_by(RotaFavorita.criado_em.desc()).all()
        return jsonify([r.to_dict() for r in rows])

    payload = request.get_json(force=True, silent=True) or {}
    fav = RotaFavorita(
        user_id=current_user.id,
        origem=payload.get("origem", "").strip(),
        destino=payload.get("destino", "").strip(),
        modo_transporte=payload.get("modo", "ape"),
        prioridade=payload.get("prioridade", "equilibrada"),
        nome_personalizado=payload.get("nome", "").strip() or None,
    )
    if not fav.origem or not fav.destino:
        return jsonify({"erro": "origem e destino obrigatórios"}), 400
    db.session.add(fav)
    db.session.commit()
    return jsonify(fav.to_dict()), 201


@auth_bp.route("/api/favoritas/<fav_id>", methods=["DELETE", "PUT"])
@login_required
def api_favorita_item(fav_id):
    fav = RotaFavorita.query.filter_by(id=fav_id, user_id=current_user.id).first()
    if not fav:
        return jsonify({"erro": "não encontrada"}), 404
    if request.method == "DELETE":
        db.session.delete(fav)
        db.session.commit()
        return jsonify({"ok": True})
    payload = request.get_json(force=True, silent=True) or {}
    fav.nome_personalizado = (payload.get("nome") or "").strip() or fav.nome_personalizado
    db.session.commit()
    return jsonify(fav.to_dict())
