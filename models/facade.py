import requests
from models.gerenciador_dados import GerenciadorDeDados
from models.estrategias import ESTRATEGIAS

# APIs gratuitas — sem necessidade de chave
_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_OSRM      = "http://router.project-osrm.org/route/v1/driving"
_HEADERS   = {"User-Agent": "SafeRoute/1.0 (PUC-SP CDIA)"}


class SafeRouteFacade:
    """
    Facade que unifica:
      1. Nominatim  → converte endereço em coordenadas
      2. OSRM       → busca rotas alternativas entre dois pontos
      3. GerenciadorDeDados → calcula risco de cada rota com dados da SSP-SP
      4. Strategy   → ordena as rotas pelo critério escolhido
    """

    def __init__(self):
        self._dados = GerenciadorDeDados()

    # ------------------------------------------------------------------ #
    # 1. Geocodificação                                                    #
    # ------------------------------------------------------------------ #
    def geocodificar(self, endereco: str) -> tuple:
        """Converte texto de endereço em (latitude, longitude)."""
        # Garante que a busca seja restrita a SP para evitar resultados errados
        sufixo = ", São Paulo, SP, Brasil"
        query  = endereco if "são paulo" in endereco.lower() or ", sp" in endereco.lower() else endereco + sufixo

        try:
            resp = requests.get(
                _NOMINATIM,
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "br"},
                headers=_HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            resultados = resp.json()
        except Exception as e:
            raise RuntimeError(f"Erro ao consultar Nominatim: {e}")

        if not resultados:
            raise ValueError(f"Endereço não encontrado: '{endereco}'. Tente ser mais específico.")

        return float(resultados[0]["lat"]), float(resultados[0]["lon"])

    # ------------------------------------------------------------------ #
    # 2. Roteamento via OSRM                                               #
    # ------------------------------------------------------------------ #
    def _buscar_rotas_osrm(self, lat1, lon1, lat2, lon2) -> list:
        """Retorna até 3 rotas alternativas com geometria (lista de pontos)."""
        url = f"{_OSRM}/{lon1},{lat1};{lon2},{lat2}"
        try:
            resp = requests.get(
                url,
                params={"alternatives": "true", "geometries": "geojson", "overview": "full"},
                headers=_HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"Erro ao consultar OSRM: {e}")

        if data.get("code") != "Ok" or not data.get("routes"):
            return []

        rotas = []
        for i, rota in enumerate(data["routes"]):
            # OSRM retorna [lon, lat] — invertemos para [lat, lon] (padrão Folium)
            coords = rota["geometry"]["coordinates"]
            pontos = [(c[1], c[0]) for c in coords]
            rotas.append({
                "nome":          f"Rota {chr(65 + i)}",
                "duracao_min":   round(rota["duration"] / 60, 1),
                "distancia_km":  round(rota["distance"] / 1000, 1),
                "pontos":        pontos,
            })

        return rotas

    # ------------------------------------------------------------------ #
    # 3. Cálculo de risco ao longo da rota                                #
    # ------------------------------------------------------------------ #
    def _risco_ponto(self, lat, lon, df, raio_km=0.4) -> float:
        """Score médio de crimes dentro do raio em torno de um ponto (vetorizado)."""
        delta = raio_km / 111  # 1 grau de latitude ≈ 111 km
        vizinhos = df[
            df["latitude"].between(lat - delta, lat + delta) &
            df["longitude"].between(lon - delta, lon + delta)
        ]
        return float(vizinhos["score_risco"].mean()) if not vizinhos.empty else 0.0

    def _risco_rota(self, pontos: list, df) -> float:
        """Amostra até 25 pontos ao longo da rota e retorna o risco médio."""
        if not pontos:
            return 0.0
        passo   = max(1, len(pontos) // 25)
        amostra = pontos[::passo]
        scores  = [self._risco_ponto(lat, lon, df) for lat, lon in amostra]
        return round(sum(scores) / len(scores), 3)

    # ------------------------------------------------------------------ #
    # 4. Método público principal                                          #
    # ------------------------------------------------------------------ #
    def obter_rota_segura(self, origem: str, destino: str, horario: str, estrategia: str = "equilibrada") -> dict:
        """
        Ponto de entrada único do sistema.
        Retorna dict com rotas ordenadas pelo critério escolhido.
        """
        df = self._dados.obter_dados().copy()

        # Filtra crimes pelo turno do horário informado
        if horario:
            try:
                hora = int(horario.split(":")[0])
                if   hora < 6:   df = df[df["hora"].between(0,  5)]
                elif hora < 12:  df = df[df["hora"].between(6,  11)]
                elif hora < 18:  df = df[df["hora"].between(12, 17)]
                else:            df = df[df["hora"].between(18, 23)]
            except (ValueError, AttributeError):
                pass  # Se horário vier mal formatado, usa todos os dados

        # Etapa 1: geocodificar
        lat1, lon1 = self.geocodificar(origem)
        lat2, lon2 = self.geocodificar(destino)

        # Etapa 2: buscar rotas no OSRM
        rotas = self._buscar_rotas_osrm(lat1, lon1, lat2, lon2)
        if not rotas:
            return {"erro": "Nenhuma rota encontrada entre os endereços informados."}

        # Etapa 3: calcular risco e normalizar duração
        dur_max = max(r["duracao_min"] for r in rotas) or 1
        for rota in rotas:
            rota["score_risco"]          = self._risco_rota(rota["pontos"], df)
            rota["duracao_normalizada"]  = rota["duracao_min"] / dur_max

        # Etapa 4: aplicar estratégia de ordenação
        estrategia_obj  = ESTRATEGIAS.get(estrategia, ESTRATEGIAS["equilibrada"])
        rotas_ordenadas = estrategia_obj.ordenar_rotas(rotas)

        # Converter score numérico em nível textual com cor
        for rota in rotas_ordenadas:
            s = rota["score_risco"]
            if s < 0.15:
                rota["nivel_risco"] = "Baixo"
                rota["cor_risco"]   = "#27ae60"
            elif s < 0.35:
                rota["nivel_risco"] = "Médio"
                rota["cor_risco"]   = "#f39c12"
            elif s < 0.6:
                rota["nivel_risco"] = "Alto"
                rota["cor_risco"]   = "#e67e22"
            else:
                rota["nivel_risco"] = "Crítico"
                rota["cor_risco"]   = "#e74c3c"

        return {
            "origem":         origem,
            "destino":        destino,
            "horario":        horario,
            "estrategia":     estrategia,
            "coord_origem":   (lat1, lon1),
            "coord_destino":  (lat2, lon2),
            "rotas":          rotas_ordenadas,
        }
