from abc import ABC, abstractmethod


class EstrategiaDeRota(ABC):
    """
    Interface base do padrão Strategy.
    Cada estratégia recebe as rotas candidatas e as ordena por critério diferente.
    """

    @abstractmethod
    def ordenar_rotas(self, rotas: list) -> list:
        """Recebe lista de rotas e retorna ordenada pelo critério da estratégia."""
        pass


class RotaMaisSegura(EstrategiaDeRota):
    """Prioriza segurança acima de tudo — pode ser mais longa."""

    def ordenar_rotas(self, rotas: list) -> list:
        # Ordena pelo score de risco (menor = mais seguro)
        return sorted(rotas, key=lambda r: r.get('score_risco', 1))


class RotaMaisRapida(EstrategiaDeRota):
    """Prioriza menor tempo de viagem — ignora nível de risco."""

    def ordenar_rotas(self, rotas: list) -> list:
        # Ordena pela duração estimada em minutos
        return sorted(rotas, key=lambda r: r.get('duracao_min', 9999))


class RotaEquilibrada(EstrategiaDeRota):
    """Equilibra segurança e tempo — recomendação padrão do sistema."""

    def ordenar_rotas(self, rotas: list) -> list:
        # Score combinado: 60% segurança + 40% tempo
        def pontuacao(rota):
            risco = rota.get('score_risco', 1)
            duracao = rota.get('duracao_normalizada', 1)
            return (risco * 0.6) + (duracao * 0.4)

        return sorted(rotas, key=pontuacao)


# Mapa de estratégias disponíveis para uso nas rotas Flask
ESTRATEGIAS = {
    'segura': RotaMaisSegura(),
    'rapida': RotaMaisRapida(),
    'equilibrada': RotaEquilibrada(),
}
