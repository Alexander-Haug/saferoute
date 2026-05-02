"""
Reports — coleta e agregação de reportes de usuários.

# TODO TIER 3 — não implementado nesta versão.
Estrutura prevista:
  - tabela reports(id, lat, lon, tipo, descricao, timestamp, validado)
  - tipos: 'iluminacao_ruim', 'sensacao_inseguranca', 'incidente', 'positivo'
  - heatmap derivado de reportes + ocorrências oficiais
  - moderação manual em /admin/reports
"""

class Reports:
    """Stub. Substituir por implementação completa em TIER 3."""

    def add(self, lat: float, lon: float, tipo: str, descricao: str = ""):
        raise NotImplementedError("TODO TIER 3")

    def heatmap(self):
        raise NotImplementedError("TODO TIER 3")
