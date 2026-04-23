import os
from dotenv import load_dotenv

# Lê o arquivo .env da pasta raiz do projeto
load_dotenv()

class Config:
    # Chave secreta do Flask (usada para sessões e cookies)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-troque-em-producao'

    # Chave da API do Google Maps (você vai fornecer depois)
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY') or ''

    # Banco de dados: SQLite em desenvolvimento, PostgreSQL em produção
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///saferoute.db'

    # Caminho para o CSV de criminalidade da SSP-SP
    CRIMES_CSV = os.environ.get('CRIMES_CSV') or 'dados/crimes.csv'

    # Modo debug: True em desenvolvimento, False em produção
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
