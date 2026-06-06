<div align="center">

# SafeRoute

**Navegue por São Paulo com mais segurança.**  
Rotas inteligentes geradas a partir de dados reais de criminalidade da SSP-SP.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![Deploy](https://img.shields.io/badge/Deploy-Render.com-46E3B7?style=flat-square&logo=render&logoColor=white)
![Status](https://img.shields.io/badge/Status-Em%20desenvolvimento-yellow?style=flat-square)

[🌐 Acessar aplicação](https://saferoute.onrender.com) &nbsp;·&nbsp; [📋 Reportar bug](https://github.com/Alexander-Haug/saferoute/issues) &nbsp;·&nbsp; [💡 Sugerir melhoria](https://github.com/Alexander-Haug/saferoute/issues)

</div>

---

## Sobre o projeto

São Paulo concentra milhares de registros de ocorrências criminais por mês — informação pública, porém inacessível ao cidadão comum. Turistas e visitantes navegam pela cidade sem qualquer noção dos horários e regiões de maior risco.

O **SafeRoute** resolve isso. A aplicação consome dados abertos da [SSP-SP](https://www.ssp.sp.gov.br/) e os transforma em um mapa interativo que sugere as **rotas mais seguras** entre dois pontos, considerando o tipo de crime, o horário e o histórico de ocorrências por bairro.

> Projeto desenvolvido no âmbito da disciplina de Engenharia de Software do curso **CDIA — PUC-SP** (3º semestre).

---

## Funcionalidades

- 🛣️ **Rotas seguras** — calcula até 3 rotas alternativas priorizando segurança, velocidade ou equilíbrio entre os dois
- 🗺️ **Mapa de risco por bairro** — visualização choropleth com segmentos de rua coloridos por nível de perigo
- 🔍 **Filtros por categoria** — filtra ocorrências por tipo (roubo, furto, homicídio etc.)
- 🕐 **Filtro por horário** — exibe o risco ajustado ao período do dia
- 🔒 **Sistema de login** — autenticação com bcrypt e proteção de rotas administrativas
- 🆘 **Botão SOS** — acesso rápido em situações de emergência
- 📱 **Responsivo** — interface acessível em desktop e dispositivos móveis

---

## Stack tecnológica

| Camada | Tecnologia |
|--------|-----------|
| **Backend** | Python 3.13 · Flask · SQLAlchemy · Gunicorn |
| **Frontend** | Jinja2 · HTML/CSS · MapLibre GL JS |
| **Processamento de dados** | Pandas · GeoPandas |
| **Geocodificação** | Nominatim (OpenStreetMap) |
| **Rotas** | OSRM |
| **Banco de dados** | SQLite (dev) · PostgreSQL via Supabase (produção) |
| **Infraestrutura** | Render.com · GitHub Actions (CI/CD) |
| **Dados** | SSP-SP · Dados Abertos SP |

> **Custo total de infraestrutura: zero.** Toda a stack utiliza planos gratuitos.

---

## Design Patterns aplicados

O projeto implementa um padrão de cada categoria do GoF:

| Padrão | Categoria | Aplicação no SafeRoute |
|--------|-----------|----------------------|
| **Singleton** | Criação | `GerenciadorDeDados` — garante que os ~500 mil registros da SSP-SP sejam carregados na memória uma única vez |
| **Facade** | Estrutural | `SafeRouteFacade` — unifica Google Maps API, SSP-SP e Dados Abertos SP em um único ponto de chamada |
| **Strategy** | Comportamental | `EstrategiaDeRota` — permite alternar entre rotas mais segura / mais rápida / equilibrada sem reescrever o motor de cálculo |

---

## Como rodar localmente

### Pré-requisitos

- Python 3.13+
- Git

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/Alexander-Haug/saferoute.git
cd saferoute

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com sua SECRET_KEY e MAPBOX_TOKEN

# 5. Inicialize o banco de dados
flask db upgrade

# 6. Rode a aplicação
flask run
```

Acesse `http://localhost:5000` no navegador.

---

## Estrutura do projeto

```
saferoute/
├── app/
│   ├── models/          # Modelos SQLAlchemy
│   ├── routes/          # Blueprints Flask
│   ├── services/        # Design patterns (Singleton, Facade, Strategy)
│   ├── static/          # CSS, JS, assets
│   └── templates/       # Templates Jinja2
├── data/                # CSVs da SSP-SP
├── tests/               # Testes pytest
├── .github/workflows/   # Pipeline CI/CD (GitHub Actions)
├── .env.example
├── requirements.txt
└── Procfile             # Configuração Render.com
```

---

## Equipe

Desenvolvido por estudantes do curso **CDIA** da **PUC-SP**:

| Contribuidor | GitHub |
|---|---|
| **Alexander Haug** ⭐ | [@Alexander-Haug](https://github.com/Alexander-Haug) |
| Arthur | - |
| Carlos Calil | [@calilprime](https://github.com/calilprime) |
| Felipe | — |
| Marina Pereira | — |

---

## Contexto acadêmico

| | |
|---|---|
| **Instituição** | PUC-SP |
| **Curso** | CDIA — Ciência de Dados e Inteligência Artificial |
| **Disciplina** | Consultoria Especializada de Apoio ao Projeto Integrado de Engenharia de Software |
| **Professora** | Lucy Mari |
| **Semestre** | 3º semestre · 2026 |

---

## Licença

Este projeto foi desenvolvido para fins acadêmicos. Dados de criminalidade utilizados são de domínio público, disponibilizados pela [SSP-SP](https://www.ssp.sp.gov.br/).

---

<div align="center">
  <sub>Feito com ☕ e Python em São Paulo.</sub>
</div>
