"""Testa SafeRouteFacade (Tarefa Design Pattern 2 — Facade)."""
from unittest.mock import patch
from services.facade import SafeRouteFacade

# Coordenadas de São Paulo (Sé) usadas como stub de geocoding
_SP_SE = (-23.5505, -46.6333)


def test_facade_inicializa():
    facade = SafeRouteFacade()
    assert facade is not None
    assert facade.loader is not None


def test_get_route_details_chaves_obrigatorias():
    """Verifica que a resposta contém as chaves esperadas."""
    facade = SafeRouteFacade()
    with patch.object(facade, "geocode", return_value=_SP_SE):
        dados = facade.get_route_details(
            "Sé, São Paulo",
            "Paulista, São Paulo",
            "2024-06-01T12:00",
            "equilibrada",
            "ape",
        )
    assert "rotas" in dados
    assert "origem" in dados
    assert "destino" in dados
    assert "recomendada" in dados
    assert isinstance(dados["rotas"], list)
    assert len(dados["rotas"]) > 0


def test_get_route_details_sem_erro_em_modo_offline():
    """Sem MAPBOX_TOKEN, deve cair no fallback sem levantar exceção."""
    facade = SafeRouteFacade()
    with patch.object(facade, "geocode", return_value=_SP_SE), \
         patch.dict("os.environ", {"MAPBOX_TOKEN": ""}):
        dados = facade.get_route_details(
            "Sé, São Paulo", "Paulista, São Paulo",
            "2024-06-01T08:00", "segura", "bicicleta",
        )
    assert dados.get("erro") is None
