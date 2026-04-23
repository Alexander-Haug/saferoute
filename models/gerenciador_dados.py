import pandas as pd
from flask import current_app

# Tipos de crime por categoria (para filtro dos cards)
CATEGORIAS = {
    'roubos_furtos': ['Roubo', 'Furto', 'Furto de Veículo', 'Roubo de Veículo'],
    'homicidios':    ['Homicídio'],
    'todos':         None,   # sem filtro
    'seguras':       None,   # usa todos, mas inverte a visualização
}


class GerenciadorDeDados:
    """
    Singleton: carrega o CSV de crimes uma única vez na primeira requisição.
    """
    _instancia    = None
    _dados_crimes = None

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
            cls._instancia._carregar_dados()
        return cls._instancia

    def _carregar_dados(self):
        caminho = current_app.config.get('CRIMES_CSV', 'dados/crimes.csv')
        try:
            self._dados_crimes = pd.read_csv(caminho)
            self._dados_crimes['score_risco'] = self._calcular_score()
            print(f"[GerenciadorDeDados] {len(self._dados_crimes)} registros carregados.")
        except FileNotFoundError:
            print(f"[GerenciadorDeDados] '{caminho}' não encontrado. Usando dados vazios.")
            self._dados_crimes = pd.DataFrame(
                columns=['ano', 'mes', 'hora', 'tipo_crime', 'bairro',
                         'latitude', 'longitude', 'qtd_ocorrencias', 'score_risco']
            )

    def _calcular_score(self):
        maximo = self._dados_crimes['qtd_ocorrencias'].max()
        return 0.0 if maximo == 0 else self._dados_crimes['qtd_ocorrencias'] / maximo

    def obter_dados(self) -> pd.DataFrame:
        return self._dados_crimes

    def obter_score_por_bairro(self, tipos_filtro: list = None) -> pd.DataFrame:
        """
        Agrega dados por bairro para o choropleth.
        Retorna: bairro, lat_media, lon_media, score_medio, total_ocorrencias
        """
        df = self._dados_crimes.copy()

        if tipos_filtro:
            df = df[df['tipo_crime'].isin(tipos_filtro)]

        if df.empty:
            return pd.DataFrame(columns=['bairro', 'lat_media', 'lon_media', 'score_medio', 'total'])

        agrupado = df.groupby('bairro').agg(
            lat_media         = ('latitude',       'mean'),
            lon_media         = ('longitude',      'mean'),
            score_medio       = ('score_risco',    'mean'),
            total             = ('qtd_ocorrencias','sum'),
        ).reset_index()

        # Normaliza score_medio entre 0 e 1 dentro do subconjunto filtrado
        mx = agrupado['score_medio'].max()
        agrupado['score_norm'] = (agrupado['score_medio'] / mx).round(3) if mx > 0 else 0

        return agrupado

    def obter_stats(self) -> dict:
        df = self._dados_crimes
        if df.empty:
            return {'total': 0, 'bairros': 0, 'tipo_mais_comum': '-'}
        return {
            'total':           len(df),
            'bairros':         df['bairro'].nunique() if 'bairro' in df.columns else 0,
            'tipo_mais_comum': df['tipo_crime'].mode()[0] if 'tipo_crime' in df.columns else '-',
        }
