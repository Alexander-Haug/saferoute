// main.js — SafeRoute

// ══════════════════════════════════════════════════════════════
// Mapa principal — MapLibre GL JS
// ══════════════════════════════════════════════════════════════
let mapaGL        = null;
let _viasFetching = false;
let _catAtiva     = 'todos';

const ESTILO_BASEMAP = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

function inicializarMapaGL() {
  const container = document.getElementById('mapa-gl');
  if (!container || typeof maplibregl === 'undefined') return;

  mapaGL = new maplibregl.Map({
    container: 'mapa-gl',
    style:     ESTILO_BASEMAP,
    center:    [-46.633, -23.548],
    zoom:      11.5,
    minZoom:   10,
    maxZoom:   16,
  });

  mapaGL.addControl(new maplibregl.NavigationControl(), 'top-right');

  mapaGL.on('load', () => {
    _atualizarMensagemLoading('Calculando risco das vias…');
    carregarViasRisco('todos');
  });

  mapaGL.on('mousemove', 'vias-risco', e => {
    mapaGL.getCanvas().style.cursor = 'pointer';
    const score = e.features[0].properties.score;
    let html;
    if (score < 0) {
      html = '<strong>Fora da área de alcance</strong><br><span style="color:#999;font-size:0.75rem">Sem dados de criminalidade</span>';
    } else {
      const nivel = score < 0.15 ? 'Baixo' : score < 0.35 ? 'Médio' : score < 0.6 ? 'Alto' : 'Crítico';
      html = `Risco: <strong>${nivel}</strong> (${(score * 100).toFixed(0)}%)`;
    }
    new maplibregl.Popup({ closeButton: false, offset: 8 })
      .setLngLat(e.lngLat)
      .setHTML(`<div style="font-size:0.82rem;padding:3px 6px;line-height:1.5;color:#000">${html}</div>`)
      .addTo(mapaGL);
  });
  mapaGL.on('mouseleave', 'vias-risco', () => {
    mapaGL.getCanvas().style.cursor = '';
    document.querySelectorAll('.maplibregl-popup').forEach(p => p.remove());
  });
}

async function carregarViasRisco(categoria) {
  if (_viasFetching || !mapaGL) return;
  _viasFetching = true;
  _mostrarLoading(true);
  _atualizarMensagemLoading('Calculando risco das vias…');

  try {
    const resp    = await fetch(`/api/rodovias?categoria=${categoria}`);
    const geojson = await resp.json();

    if (mapaGL.getSource('vias')) {
      mapaGL.getSource('vias').setData(geojson);
    } else {
      const primeiraLabel = mapaGL.getStyle().layers.find(l => l.type === 'symbol')?.id;

      mapaGL.addSource('vias', { type: 'geojson', data: geojson, buffer: 64 });

      mapaGL.addLayer({
        id: 'vias-sombra', type: 'line', source: 'vias',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color':   '#fff',
          'line-opacity': 0.35,
          'line-width': ['interpolate', ['linear'], ['zoom'],
            9,  ['*', ['get', 'largura'], 0.6],
            13, ['*', ['get', 'largura'], 3.2],
            16, ['*', ['get', 'largura'], 9.0],
          ],
          'line-blur': 2,
        },
      }, primeiraLabel);

      mapaGL.addLayer({
        id: 'vias-risco', type: 'line', source: 'vias',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': [
            'case',
            ['<', ['get', 'score'], 0], '#b0b0b0',
            ['interpolate', ['linear'], ['get', 'score'],
              0.00, '#27ae60',
              0.35, '#f1c40f',
              0.60, '#e67e22',
              1.00, '#e74c3c',
            ],
          ],
          'line-width': ['interpolate', ['linear'], ['zoom'],
            9,  ['*', ['get', 'largura'], 0.30],
            11, ['*', ['get', 'largura'], 0.80],
            13, ['*', ['get', 'largura'], 2.00],
            16, ['*', ['get', 'largura'], 6.00],
          ],
          'line-opacity': 0.80,
        },
      }, primeiraLabel);
    }
    _mostrarLoading(false);
  } catch (err) {
    console.error('[SafeRoute] Erro ao carregar vias:', err);
    _atualizarMensagemLoading('Erro ao carregar mapa. Tente recarregar a página.');
  } finally {
    _viasFetching = false;
  }
}

function _mostrarLoading(mostrar) {
  const el = document.getElementById('mapa-loading');
  if (el) el.style.display = mostrar ? 'flex' : 'none';
}

function _atualizarMensagemLoading(msg) {
  const el = document.getElementById('mapa-loading-msg');
  if (el) el.textContent = msg;
}

// ══════════════════════════════════════════════════════════════
// Cards de categoria
// ══════════════════════════════════════════════════════════════
function filtrarCategoria(btnClicado) {
  const cat = btnClicado.dataset.cat;
  if (cat === _catAtiva || _viasFetching) return;
  _catAtiva = cat;
  document.querySelectorAll('.card-cat').forEach(b => b.classList.remove('ativo'));
  btnClicado.classList.add('ativo');
  carregarViasRisco(cat);
}

// ══════════════════════════════════════════════════════════════
// Modo escuro / claro
// ══════════════════════════════════════════════════════════════
function aplicarTema(tema) {
  document.documentElement.setAttribute('data-tema', tema);
  const lua = document.getElementById('icone-lua');
  const sol = document.getElementById('icone-sol');
  if (lua && sol) {
    lua.style.display = tema === 'claro' ? 'block' : 'none';
    sol.style.display = tema === 'claro' ? 'none'  : 'block';
  }
}

function alternarTema() {
  const atual = document.documentElement.getAttribute('data-tema') || 'claro';
  const novo  = atual === 'claro' ? 'escuro' : 'claro';
  aplicarTema(novo);
  localStorage.setItem('saferoute-tema', novo);
}

function carregarTema() {
  aplicarTema(localStorage.getItem('saferoute-tema') || 'claro');
}

// ══════════════════════════════════════════════════════════════
// Horário padrão = agora em SP
// ══════════════════════════════════════════════════════════════
function definirHorarioAtual() {
  const campo = document.getElementById('horario');
  if (!campo) return;
  campo.value = new Date().toLocaleTimeString('pt-BR', {
    timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit',
  });
}

// ══════════════════════════════════════════════════════════════
// Capa de entrada
// ══════════════════════════════════════════════════════════════
function rolarParaApp() {
  const app = document.getElementById('app');
  if (app) app.scrollIntoView({ behavior: 'smooth' });
}

// ══════════════════════════════════════════════════════════════
// Painel de reporte
// ══════════════════════════════════════════════════════════════
function toggleReporte() {
  const p = document.getElementById('painel-reporte');
  if (!p) return;
  const abrindo = p.style.display === 'none';
  p.style.display = abrindo ? 'block' : 'none';
  if (abrindo) capturarLocalizacaoReporte();
}

function capturarLocalizacaoReporte() {
  const status = document.getElementById('status-localizacao');
  if (!navigator.geolocation) {
    if (status) status.textContent = 'Geolocalização não disponível.';
    return;
  }
  navigator.geolocation.getCurrentPosition(
    pos => {
      document.getElementById('campo-lat').value = pos.coords.latitude;
      document.getElementById('campo-lon').value = pos.coords.longitude;
      if (status) { status.textContent = 'Localização capturada.'; status.style.color = '#27ae60'; }
    },
    () => { if (status) status.textContent = 'Não foi possível obter localização.'; }
  );
}

// ══════════════════════════════════════════════════════════════
// Alerta de área de risco (Fase 7)
// ══════════════════════════════════════════════════════════════
let _ultimaVerificacao = 0;

function iniciarMonitoramento() {
  if (!navigator.geolocation) return;
  navigator.geolocation.watchPosition(pos => {
    const agora = Date.now();
    if (agora - _ultimaVerificacao < 30000) return;
    _ultimaVerificacao = agora;
    verificarRisco(pos.coords.latitude, pos.coords.longitude);
  }, () => {}, { enableHighAccuracy: false, maximumAge: 60000 });
}

function verificarRisco(lat, lon) {
  fetch(`/api/verificar-risco?lat=${lat}&lon=${lon}`)
    .then(r => r.json())
    .then(data => {
      const alerta = document.getElementById('alerta-risco');
      if (!alerta) return;
      if (data.nivel === 'Alto' || data.nivel === 'Crítico') {
        document.getElementById('alerta-nivel').textContent = data.nivel;
        const s = document.getElementById('alerta-score');
        if (s) s.textContent = ` (score ${data.score}%)`;
        alerta.style.display = 'flex';
        alerta.style.borderLeftColor = data.cor;
      } else {
        alerta.style.display = 'none';
      }
    }).catch(() => {});
}

function fecharAlerta() {
  const el = document.getElementById('alerta-risco');
  if (el) el.style.display = 'none';
}

// ══════════════════════════════════════════════════════════════
// Inicialização
// ══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  carregarTema();
  definirHorarioAtual();
  inicializarMapaGL();
  iniciarMonitoramento();
});
