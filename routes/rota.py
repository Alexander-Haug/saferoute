import folium
from flask import Blueprint, render_template, request, flash, redirect, url_for
from models.facade import SafeRouteFacade
from database.db import get_db

rota_bp = Blueprint("rota", __name__)

NOMES_ESTRATEGIA = {
    "segura":      "Mais Segura",
    "rapida":      "Mais Rápida",
    "equilibrada": "Equilibrada",
}


def _gerar_mapa_resultado(resultado: dict) -> str:
    """Gera mapa Folium com as rotas desenhadas e marcadores de origem/destino."""
    lat1, lon1 = resultado["coord_origem"]
    lat2, lon2 = resultado["coord_destino"]

    centro = ((lat1 + lat2) / 2, (lon1 + lon2) / 2)
    mapa   = folium.Map(location=centro, zoom_start=13, tiles="CartoDB positron")

    for i, rota in enumerate(resultado["rotas"]):
        folium.PolyLine(
            rota["pontos"],
            color=rota["cor_risco"],
            weight=7 if i == 0 else 4,
            opacity=1.0 if i == 0 else 0.45,
            tooltip=f"{rota['nome']} · {rota['nivel_risco']} risco · {rota['duracao_min']} min · {rota['distancia_km']} km",
        ).add_to(mapa)

    folium.Marker([lat1, lon1], popup="Origem",
                  icon=folium.Icon(color="blue", icon="circle", prefix="fa")).add_to(mapa)
    folium.Marker([lat2, lon2], popup="Destino",
                  icon=folium.Icon(color="red", icon="flag", prefix="fa")).add_to(mapa)

    return mapa._repr_html_()


def _salvar_historico(origem, destino, horario, estrategia, resultado):
    """Persiste a busca no banco. Falha silenciosa para não bloquear o usuário."""
    try:
        melhor = resultado["rotas"][0] if resultado.get("rotas") else {}
        conn = get_db()
        conn.execute(
            """INSERT INTO historico_rotas
               (origem, destino, horario, estrategia, score_risco, duracao_min, distancia_km)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                origem,
                destino,
                horario,
                estrategia,
                melhor.get("score_risco", 0),
                melhor.get("duracao_min", 0),
                melhor.get("distancia_km", 0),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # histórico é secundário — nunca bloqueia o fluxo principal


@rota_bp.route("/rota", methods=["GET", "POST"])
def buscar_rota():
    """Recebe o formulário, calcula rotas e exibe resultado."""
    if request.method == "POST":
        origem     = request.form.get("origem", "").strip()
        destino    = request.form.get("destino", "").strip()
        horario    = request.form.get("horario", "08:00")
        estrategia = request.form.get("estrategia", "equilibrada")

        if not origem or not destino:
            flash("Preencha origem e destino.", "error")
            return redirect(url_for("mapa.index"))

        try:
            facade    = SafeRouteFacade()
            resultado = facade.obter_rota_segura(origem, destino, horario, estrategia)
        except (ValueError, RuntimeError) as e:
            flash(str(e), "error")
            return redirect(url_for("mapa.index"))

        if "erro" in resultado:
            flash(resultado["erro"], "error")
            return redirect(url_for("mapa.index"))

        _salvar_historico(origem, destino, horario, estrategia, resultado)

        return render_template(
            "resultado.html",
            resultado=resultado,
            mapa_html=_gerar_mapa_resultado(resultado),
            nome_estrategia=NOMES_ESTRATEGIA.get(estrategia, estrategia),
        )

    return redirect(url_for("mapa.index"))


@rota_bp.route("/historico")
def historico():
    """Exibe as últimas buscas de rotas realizadas."""
    try:
        conn  = get_db()
        rotas = conn.execute(
            """SELECT origem, destino, horario, estrategia,
                      score_risco, duracao_min, distancia_km, criado_em
               FROM historico_rotas
               ORDER BY criado_em DESC
               LIMIT 30"""
        ).fetchall()
        conn.close()
        registros = [dict(r) for r in rotas]
    except Exception:
        registros = []

    return render_template("historico.html", registros=registros)
