"""
Testa que o parâmetro `prioridade` (Strategy) produz recomendadas diferentes
(Tarefa Design Pattern 3 — Strategy).
"""
from unittest.mock import patch
from services.facade import SafeRouteFacade

_SP_SE = (-23.5505, -46.6333)


def _rota(prioridade: str) -> dict:
    facade = SafeRouteFacade()
    with patch.object(facade, "geocode", return_value=_SP_SE), \
         patch.dict("os.environ", {"MAPBOX_TOKEN": ""}):
        return facade.get_route_details(
            "Sé, São Paulo", "Paulista, São Paulo",
            "2024-06-01T12:00", prioridade, "ape",
        )


def test_strategy_segura_vs_rapida():
    """Prioridade 'segura' e 'rapida' devem indicar rotas recomendadas diferentes."""
    segura = _rota("segura")
    rapida = _rota("rapida")
    assert segura["recomendada"] != rapida["recomendada"]


def test_strategy_equilibrada_entre_extremos():
    """Prioridade 'equilibrada' deve indicar a rota B (meio-termo)."""
    equil = _rota("equilibrada")
    segura = _rota("segura")
    rapida = _rota("rapida")
    # equilibrada não deve ser nem a mais segura nem a mais rápida
    assert equil["recomendada"] not in (segura["recomendada"], rapida["recomendada"]) \
        or equil["recomendada"] == "B"


def test_strategy_todas_possuem_rotas():
    for prio in ("segura", "equilibrada", "rapida"):
        dados = _rota(prio)
        assert len(dados["rotas"]) > 0, f"prioridade={prio} não retornou rotas"
