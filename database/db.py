import sqlite3

DATABASE = 'saferoute.db'


def get_db():
    """Abre conexão com o banco SQLite. Rows acessíveis como dicionários."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria e migra as tabelas do banco na inicialização do app."""
    conn   = get_db()
    cursor = conn.cursor()

    # Tabela de ocorrências reportadas pelos usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo        TEXT NOT NULL,
            latitude    REAL,
            longitude   REAL,
            descricao   TEXT,
            criado_em   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de histórico de rotas (endereços em texto — sem coordenadas, LGPD)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_rotas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            origem        TEXT,
            destino       TEXT,
            horario       TEXT,
            estrategia    TEXT,
            score_risco   REAL,
            duracao_min   REAL,
            distancia_km  REAL,
            criado_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migração: adiciona colunas novas se a tabela já existia sem elas
    colunas_existentes = {
        row[1] for row in cursor.execute("PRAGMA table_info(historico_rotas)")
    }
    for coluna, tipo in [("horario", "TEXT"), ("duracao_min", "REAL"), ("distancia_km", "REAL")]:
        if coluna not in colunas_existentes:
            cursor.execute(f"ALTER TABLE historico_rotas ADD COLUMN {coluna} {tipo}")

    conn.commit()
    conn.close()
    print("[DB] Banco de dados inicializado.")
