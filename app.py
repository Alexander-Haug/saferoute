from flask import Flask
from config import Config


def criar_app():
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Registra os grupos de rotas (blueprints)
    from routes.mapa import mapa_bp
    from routes.rota import rota_bp
    from routes.ocorrencias import ocorrencias_bp

    app.register_blueprint(mapa_bp)
    app.register_blueprint(rota_bp)
    app.register_blueprint(ocorrencias_bp)

    # Cria as tabelas do banco de dados se ainda não existirem
    with app.app_context():
        from database.db import init_db
        init_db()

    return app


# Cria a instância global do app
app = criar_app()

if __name__ == '__main__':
    # Roda o servidor de desenvolvimento em http://localhost:5000
    app.run(debug=app.config['DEBUG'])
