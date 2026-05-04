# 📊 SafeRoute — Progresso & Roadmap

**Última atualização:** sessão atual
**Versão deployada:** v2.x → https://saferoute-rqcj.onrender.com
**Repositório:** https://github.com/SEU_USUARIO/saferoute

---

## ✅ COMPLETO

### Core (v1)
- [x] Landing page separada do app
- [x] Tela de resultado com 3 rotas
- [x] Geolocalização com reverse geocoding
- [x] Toggle "Agora vs Depois"
- [x] Modo de transporte (a pé / bici / carro / TP)
- [x] Cards de categoria como filtros
- [x] Tooltip de metodologia
- [x] Compartilhar rota via link
- [x] Bottom-sheet arrastável no mobile
- [x] Loading feedback
- [x] Versionamento + metadata
- [x] Favoritas (DB ou localStorage)
- [x] Cache de geocoding com fuzzy match
- [x] Telemetria anônima + dashboard

### Auth (Caminho B)
- [x] Login / Registro / Logout
- [x] bcrypt + Flask-Login
- [x] SQLite local / PostgreSQL produção
- [x] Perfil: editar nome, alterar senha, soft-delete

### v2 — App-feel
- [x] Top bar com glass-blur
- [x] Bottom navigation 4 itens
- [x] Splash screen
- [x] Dark mode com persistência

### Bugs corrigidos
- [x] Geocoding broken (Mapbox Geocoding com proximity SP + bbox)
- [x] Modo de transporte ignorado (label-wrap pattern)
- [x] Rotas linha reta (Mapbox Directions API)
- [x] 3 rotas idênticas (alternatives=true)
- [x] Erro "não localizei" (validação prévia + dist >80km guard)
- [x] Título sempre "3 rotas calculadas" (dinâmico)
- [x] /mapa /buscar 404 (redirects 301)
- [x] Popup ilegível (qtd, hora típica, mês/ano)
- [x] Checkbox sem estilo (accent-color)
- [x] Sheet sobrepondo bottom nav (z-index + bottom + peek 140px)

### v3 — App polish
- [x] Logo SVG
- [x] Reportar como FAB flutuante (não na nav)
- [x] Pin geolocalização atual (Geolocate auto-trigger)
- [x] Rotas reais sem síntese (1, 2 ou 3 conforme Mapbox)
- [x] Reportar sem login (anônimo)
- [x] Tema removido do perfil
- [x] Landing redesenhada (Hero + 3 passos + Diferenciais + FAQ)
- [x] Skeleton loading no mapa
- [x] GPS button destacado
- [x] Pills com seleção visível (azul brilhante)
- [x] Limpar histórico (individual + tudo)
- [x] MOBILE_APP.md (PWA + Capacitor + Tauri)
- [x] PACKAGING.md (7-Zip + age + GPG)

---

## 🚧 EM ANDAMENTO / PRÓXIMO

### Esta sessão
- [ ] **Autocomplete de endereços** (Mapbox Suggest API + dropdown debounced)
- [ ] **Heatmap toggle** (alternar entre clusters numerados e heatmap puro)
- [ ] **Slider de horário no mapa** (recalcula score por hora arrastando)
- [ ] **Tooltip hover em cluster** (queryRenderedFeatures + custom popup)

### Próxima sessão

#### Bugs mobile não-resolvidos
**O usuário reportou que a interface do celular continua "meio bugada"
e mandou 2 vídeos WhatsApp que eu não consigo abrir.** Fiz melhorias
genéricas (font-size 16px pra evitar zoom iOS, foco em input abre sheet,
fade nos chips horizontais, slider e viewmode reposicionados) mas pode
ter bug específico que só os vídeos mostram.

**Próxima sessão pedir prints ao invés de vídeo.**

#### Bônus que ficou pra fazer
- [ ] Colorir segmentos da rota recomendada por score local
      (verde→amarelo→vermelho), quebrando a polyline em sub-segmentos
      por bairro
- [ ] OSRM como alternativa pro Mapbox Directions (fallback gratuito)
- [ ] Reset de senha por email (SendGrid)
- [ ] JWT + refresh tokens (substituir Flask-Login)
- [ ] Confirmação de email no registro

### Backlog longo prazo
- [ ] Reportes aparecem como overlay no mapa (com moderação)
- [ ] Notificações push (PWA + service worker)
- [ ] Multi-cidade (não só São Paulo)
- [ ] App Capacitor publicado nas lojas
- [ ] Testes (pytest + jest)

---

## 🗂️ Estrutura atual

```
saferoute-melhorado/
├── app.py
├── controllers/
│   ├── routes.py       (páginas + API rotas/mapa/info)
│   ├── auth.py         (login/registro/perfil/favoritas)
│   ├── reports.py      (reportar - anônimo permitido)
│   └── admin.py        (dashboard analytics)
├── services/
│   └── facade.py       (Mapbox Geocoding + Directions + scoring)
├── models/
│   ├── data_loader.py  (Singleton CSV crimes.csv)
│   ├── db.py           (User, RotaFavorita, HistoricoBusca, Report)
│   ├── geocoding_cache.py (SQLite cache fuzzy)
│   └── analytics.py    (telemetria sem PII)
├── templates/
│   ├── base.html       (layout master)
│   ├── landing.html    (hero + features + FAQ)
│   ├── app.html        (mapa + sheet + pills)
│   ├── rota_resultado.html
│   ├── perfil.html
│   ├── reportar.html
│   ├── historico.html
│   ├── admin_analytics.html
│   └── auth/{login,register}.html
├── static/
│   ├── css/{base,responsive,components}.css
│   ├── js/{mapa,app,bottom_sheet,dark_mode,
│   │       favoritas,filtros,geolocation,
│   │       compartilhar,loading}.js
│   ├── logo.svg
│   └── manifest.json
├── data/
│   ├── crimes.csv      (15k SSP-SP)
│   └── metadata.json
├── README.md
├── MOBILE_APP.md
├── PACKAGING.md
└── PROGRESS.md         (este arquivo)
```

---

## 🔑 Variáveis de ambiente (Render)

| Key | Value |
|---|---|
| `MAPBOX_TOKEN` | Token público (`pk....`) com URL restrictions |
| `SECRET_KEY` | 64 chars aleatórios |
| `DATABASE_URL` | postgresql://... do Render |
| `FLASK_DEBUG` | `0` em produção |

---

## 🔄 Como continuar em nova conversa Claude

Cole isto no início:

> Estou trabalhando no projeto SafeRoute (Flask + Mapbox).
> Leia o arquivo `PROGRESS.md` no diretório
> `C:\Users\calil\Downloads\CLAUDE CODE\saferoute-melhorado\` pra entender
> o estado atual. Continue de onde a lista "🚧 EM ANDAMENTO" indica.
