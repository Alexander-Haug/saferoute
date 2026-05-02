# SafeRoute v2

Aplicativo de **rotas seguras em São Paulo** — projeto acadêmico PUC-SP.
Recomenda 3 alternativas de trajeto (segura, equilibrada, rápida) calculando um
score de risco a partir de ocorrências da SSP-SP, ponderado por horário e modo
de transporte.

**Stack:** Python 3.13 · Flask · SQLAlchemy · SQLite (dev) / PostgreSQL (prod) ·
bcrypt + Flask-Login · Mapbox GL JS · Nominatim.

---

## ✨ O que está pronto nesta versão

### TIER 1 — UI/UX
- [x] Landing separada do app (`/` vs `/app`)
- [x] Tela de resultado com 3 rotas comparáveis e botão "Iniciar navegação"
- [x] Geolocalização (📍) com reverse-geocode
- [x] Toggle "Agora vs Depois" persistente em sessionStorage
- [x] Modo de transporte como pill-select (multiplicador no score)
- [x] Cards/chips de categoria filtram o mapa em tempo real
- [x] Tooltip com metodologia
- [x] Compartilhar rota por link curto

### TIER 2 — Otimizações
- [x] Bottom-sheet **arrastável de verdade** no mobile
- [x] Loading "Calculando rotas seguras… consultando 15.000 ocorrências"
- [x] Versionamento dinâmico (`/api/info` + footer)
- [x] Favoritas — sincronizadas no DB (logado) ou localStorage (convidado)
- [x] Cache local de geocoding com fuzzy match (SQLite, 30 dias TTL)
- [x] Telemetria anônima + dashboard `/admin/analytics`

### v2 (Caminho B) — App-feel + auth
- [x] Visual app-like (top bar fina, **bottom navigation**, splash, dark mode)
- [x] Mapbox GL JS com **heatmap** + **clusters** + popups
- [x] Login / Registro / Perfil (bcrypt, Flask-Login, SQLite local)
- [x] Histórico no DB quando logado
- [x] Favoritas no DB + soft-delete de conta

### TODO TIER 3 (não implementado)
- [ ] Reportes de iluminação ruim (`models/reports.py` é stub)
- [ ] JWT + refresh token (atualmente só sessão Flask-Login)
- [ ] Confirmação de email via SendGrid
- [ ] OSRM real (rotas geometricamente reais em vez de linhas didáticas)

---

## 🏃 Rodar localmente (5 min)

```bash
# 1. Clone
git clone https://github.com/SEU_USUARIO/saferoute.git
cd saferoute

# 2. Ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# 3. Dependências
pip install -r requirements.txt

# 4. Variáveis de ambiente
cp .env.example .env
# Edite .env e preencha MAPBOX_TOKEN com SEU token público (pk....)
# Gere SECRET_KEY com: python -c "import secrets; print(secrets.token_hex(32))"

# 5. Rodar
python app.py
# → http://localhost:5000
```

A primeira execução cria automaticamente:
- `data/saferoute.db` — usuários, favoritas, histórico
- `data/geocode_cache.db` — cache de geocoding
- `data/analytics.db` — telemetria

---

## 🔑 Conta demo (criada por você manualmente)

Não há seed automático. Para criar a conta `demo`:

1. Suba o app local.
2. Acesse http://localhost:5000/registro
3. Preencha:
   - Nome: `Demo User`
   - Email: `demo@saferoute.com`
   - Senha: `Senha123!`

Pronto, login feito. O mesmo vale na produção.

---

## 🚀 Deploy no Render (passo a passo manual)

> Você confirmou que já tem conta no Render e o repo `saferoute` no GitHub.
> Estes são os passos que **você precisa fazer**, com os valores prontos pra copiar.

### A) Subir pro GitHub

```bash
cd saferoute-melhorado
git init
git remote add origin git@github.com:SEU_USUARIO/saferoute.git
git add .
git status            # CONFIRA que .env NÃO está na lista (o .gitignore já bloqueia)
git commit -m "feat: SafeRoute v2 com auth, dark mode e Mapbox"
git branch -M main
git push -u origin main
```

### B) Provisionar o PostgreSQL no Render

1. Render dashboard → **New** → **PostgreSQL**
2. Nome: `saferoute-db` · Region: `Oregon` (ou a mesma do web service) · Plan: **Free**
3. **Create Database**
4. Quando terminar, copie a **Internal Database URL** (começa com `postgresql://`).

### C) Criar o Web Service

1. Render dashboard → **New** → **Web Service**
2. Conecte o repo `saferoute`
3. Configure:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Plan:** Free
4. Em **Environment Variables**, adicione:

   | Key | Value |
   |---|---|
   | `MAPBOX_TOKEN` | seu token público novo (`pk....`) — **NÃO o que vazou no chat** |
   | `SECRET_KEY` | rode `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `DATABASE_URL` | a Internal URL do passo B |
   | `FLASK_DEBUG` | `0` |

5. **Create Web Service**. O primeiro deploy demora ~3 min.
6. Quando ficar verde, abra a URL pública (algo como `https://saferoute.onrender.com`).

### D) Criar a conta demo

Acesse `https://SEU-SAFEROUTE.onrender.com/registro` e crie a conta `demo@saferoute.com` / `Senha123!` (ou a sua).

---

## 🗂️ Estrutura

```
saferoute-melhorado/
├── app.py                       # Entry point Flask + factory
├── Procfile                     # gunicorn app:app  (Render usa)
├── runtime.txt                  # python-3.13.0
├── requirements.txt
├── .env.example                 # Template — NUNCA commite .env
├── .gitignore
├── data/
│   ├── crimes.csv               # 15k ocorrências SSP-SP (fonte original)
│   └── metadata.json            # versão + data
├── controllers/
│   ├── routes.py                # Páginas + API (rotas, mapa, info)
│   ├── auth.py                  # Login, registro, perfil, favoritas API
│   └── admin.py                 # /admin/analytics
├── services/
│   └── facade.py                # SafeRouteFacade (geocode, scoring, rotas)
├── models/
│   ├── data_loader.py           # Singleton: lê CSV, calcula score (com modo)
│   ├── geocoding_cache.py       # Cache SQLite + fuzzy match difflib
│   ├── analytics.py             # Telemetria SQLite (sem PII)
│   ├── db.py                    # User, RotaFavorita, HistoricoBusca
│   └── reports.py               # [TODO TIER 3]
├── templates/
│   ├── base.html                # Layout master: top bar + bottom nav + splash
│   ├── landing.html             # Hero + features + CTA
│   ├── app.html                 # Mapa + bottom sheet
│   ├── rota_resultado.html      # 3 rotas + comparativo
│   ├── perfil.html              # Dados, senha, favoritas, histórico
│   ├── historico.html
│   ├── admin_analytics.html
│   └── auth/
│       ├── login.html
│       └── register.html
└── static/
    ├── css/                     # base, responsive (mobile-first), components
    ├── js/
    │   ├── mapa.js              # Mapbox GL: heatmap + clusters + 3 rotas
    │   ├── bottom_sheet.js      # Drag arrastável real
    │   ├── dark_mode.js         # Toggle persistente
    │   ├── geolocation.js       # 📍 + reverse geocode
    │   ├── filtros.js           # Chips de categoria
    │   ├── favoritas.js         # DB ou localStorage
    │   ├── compartilhar.js      # Web Share API + clipboard
    │   ├── loading.js           # Spinner + toast helper
    │   └── app.js               # Persistência de prefs no formulário
    ├── manifest.json            # PWA mínimo
    └── logo.png
```

---

## 🔐 Segurança

- Senhas com **bcrypt** (10 rounds) via lib `bcrypt`.
- Sessões via **Flask-Login** (cookie assinado com `SECRET_KEY`).
- `MAPBOX_TOKEN` é exposto no HTML **propositalmente** — tokens `pk.` são feitos pra isso.
  O token **secreto** (`sk....`) **nunca** entra no app.
- `.env` é bloqueado pelo `.gitignore`. Não commite.
- Telemetria não armazena email, lat/lon de origem/destino nem user_id.

---

## 📋 Checklist visível para o professor

- [x] Login + Registro funcionando
- [x] Perfil com edição + alteração de senha + soft delete
- [x] Mapa Mapbox com heatmap colorido (verde→amarelo→vermelho)
- [x] 3 rotas calculadas com cores distintas
- [x] Score de risco 0-10 visível
- [x] Salvar favorita (DB se logado, localStorage se convidado)
- [x] Histórico funcional
- [x] Filtros de categoria reativos
- [x] Dark mode com persistência
- [x] Mobile responsivo + bottom sheet drag
- [x] Bottom navigation estilo nativo
- [x] Telemetria + dashboard admin

---

## ❓ FAQ rápido

**O mapa aparece em branco / "Token Mapbox não configurado"?**
→ Crie um token público novo em https://account.mapbox.com/access-tokens/ e
   coloque no `.env` (local) ou nas Environment Variables do Render (prod).

**Esqueci a senha do demo, como reseto?**
→ Esta versão não tem reset por email (depende de SendGrid, deferido p/ TIER 3).
   Apague `data/saferoute.db` localmente e registre de novo. Em produção,
   conecte ao banco PostgreSQL e atualize o `senha_hash` direto.

**Posso usar OSRM pra rotas reais?**
→ Sim, mas é TIER 3. Hoje as polylines são interpoladas didaticamente
   (ponto médio com offset). Para OSRM, troque `linha()` em `services/facade.py`
   por chamada à `https://router.project-osrm.org/route/v1/...`.
