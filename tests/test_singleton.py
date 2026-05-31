"""Testa que DataLoader é um Singleton (Tarefa Design Pattern 1)."""
from models.data_loader import DataLoader


def test_singleton_mesma_instancia():
    a = DataLoader.instance()
    b = DataLoader.instance()
    assert a is b, "DataLoader.instance() deve retornar sempre o mesmo objeto"


def test_singleton_tipo():
    assert isinstance(DataLoader.instance(), DataLoader)
