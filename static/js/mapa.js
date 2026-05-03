/* mapa.js — integração Mapbox GL JS.
 * Mostra heatmap + cluster de ocorrências (app.html) e
 * desenha 3 rotas no resultado.
 */
window.SafeRoute = window.SafeRoute || {};

const SP_CENTER = [-46.6333, -23.5505];
const STYLE_LIGHT = 'mapbox://styles/mapbox/light-v11';
const STYLE_DARK  = 'mapbox://styles/mapbox/dark-v11';

function currentStyle() {
  return document.documentElement.getAttribute('data-theme') === 'escuro'
    ? STYLE_DARK : STYLE_LIGHT;
}

function ensureToken() {
  const t = (window.SR_CONFIG || {}).mapboxToken;
  if (!t) {
    console.warn('[SafeRoute] MAPBOX_TOKEN não configurado. ' +
      'Crie um token público no Mapbox e coloque no .env como MAPBOX_TOKEN=pk....');
    return false;
  }
  mapboxgl.accessToken = t;
  return true;
}

/* ---------- Mapa principal (app.html) ---------- */
function initMainMap() {
  const el = document.getElementById('map');
  if (!el || !ensureToken()) {
    if (el) el.innerHTML = '<div style="padding:24px;text-align:center">' +
      '⚠️ Token Mapbox não configurado.<br>Defina <code>MAPBOX_TOKEN</code> no <code>.env</code>.</div>';
    return;
  }

  const map = new mapboxgl.Map({
    container: 'map', style: currentStyle(),
    center: SP_CENTER, zoom: 11.5, pitch: 0,
  });
  map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');
  // Geolocate: mostra ponto azul + acurácia + pin de localização atual
  const geolocate = new mapboxgl.GeolocateControl({
    positionOptions: { enableHighAccuracy: true },
    trackUserLocation: true, showUserHeading: true, showAccuracyCircle: true,
  });
  map.addControl(geolocate, 'top-right');

  let currentFilter = 'all';

  map.on('load', async () => {
    // Tira o skeleton só quando o mapa de fato carregou
    document.getElementById('mapSkeleton')?.classList.add('is-hidden');
    setTimeout(() => document.getElementById('mapSkeleton')?.remove(), 400);
    await loadOccurrences(map, currentFilter);
    // Tenta acionar geolocalização automática (silenciosamente — usuário precisa permitir)
    try { geolocate.trigger(); } catch {}
  });

  // Re-renderiza ao mudar de tema
  new MutationObserver(() => map.setStyle(currentStyle()))
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  map.on('style.load', () => loadOccurrences(map, currentFilter));

  // Hook pros chips de filtro
  window.SafeRoute._setMapFilter = async (f) => {
    currentFilter = f;
    await loadOccurrences(map, f);
  };

  window.SafeRoute._mainMap = map;
}

async function loadOccurrences(map, filter) {
  const r = await fetch(`/api/map-data?filter=${encodeURIComponent(filter)}`);
  const data = await r.json();
  const SRC = 'ocorrencias';

  if (map.getSource(SRC)) {
    map.getSource(SRC).setData(data);
    return;
  }

  map.addSource(SRC, {
    type: 'geojson', data,
    cluster: true, clusterMaxZoom: 14, clusterRadius: 40,
  });

  // Heatmap
  map.addLayer({
    id: 'oc-heat', type: 'heatmap', source: SRC, maxzoom: 15,
    paint: {
      'heatmap-weight': ['interpolate', ['linear'], ['get', 'qtd'], 0, 0, 10, 1],
      'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 15, 3],
      'heatmap-color': [
        'interpolate', ['linear'], ['heatmap-density'],
        0, 'rgba(16,185,129,0)',
        0.2, 'rgba(16,185,129,0.5)',
        0.5, 'rgba(251,191,36,0.6)',
        0.8, 'rgba(239,68,68,0.7)',
        1, 'rgba(220,38,38,0.85)'
      ],
      'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 12, 15, 30],
      'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 7, 0.85, 15, 0.4],
    },
  });

  // Clusters
  map.addLayer({
    id: 'oc-clusters', type: 'circle', source: SRC, filter: ['has', 'point_count'],
    paint: {
      'circle-color': ['step', ['get', 'point_count'], '#10B981', 20, '#FBBF24', 50, '#EF4444'],
      'circle-radius': ['step', ['get', 'point_count'], 14, 20, 18, 50, 24],
      'circle-stroke-width': 2, 'circle-stroke-color': '#fff',
    },
  });
  map.addLayer({
    id: 'oc-cluster-count', type: 'symbol', source: SRC, filter: ['has', 'point_count'],
    layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12 },
    paint: { 'text-color': '#fff' },
  });

  // Pontos individuais (zoom alto)
  map.addLayer({
    id: 'oc-points', type: 'circle', source: SRC, filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-color': [
        'match', ['get', 'grupo'],
        'roubos_furtos', '#EF4444',
        'homicidios', '#7F1D1D',
        'violencia', '#F97316',
        '#3B82F6'
      ],
      'circle-radius': 5, 'circle-stroke-width': 1, 'circle-stroke-color': '#fff',
    },
  });

  // Bug 8 — popup legível com qtd, faixa de horário e mês/ano
  const MESES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  map.on('click', 'oc-points', (e) => {
    const f = e.features[0];
    const p = f.properties;
    const qtdLabel = `${p.qtd} ${p.qtd == 1 ? 'ocorrência registrada' : 'ocorrências registradas'}`;
    const horaIni = parseInt(p.hora, 10);
    const horaFim = (horaIni + 1) % 24;
    const mes = MESES[(parseInt(p.mes, 10) - 1) % 12] || p.mes;
    new mapboxgl.Popup({ closeButton: false, maxWidth: '260px' })
      .setLngLat(f.geometry.coordinates)
      .setHTML(`
        <div class="sr-popup">
          <strong class="sr-popup-title">${p.tipo}</strong>
          <div class="sr-popup-row">📍 ${p.bairro}</div>
          <div class="sr-popup-row">🔢 ${qtdLabel}</div>
          <div class="sr-popup-row">🕐 Horário típico: entre ${horaIni}h e ${horaFim}h</div>
          <div class="sr-popup-row sr-popup-mute">📅 Período: ${mes}/${p.ano}</div>
        </div>
      `).addTo(map);
  });
  map.on('mouseenter', 'oc-points', () => map.getCanvas().style.cursor = 'pointer');
  map.on('mouseleave', 'oc-points', () => map.getCanvas().style.cursor = '');

  // Click em cluster → zoom in
  map.on('click', 'oc-clusters', (e) => {
    const f = e.features[0];
    map.getSource(SRC).getClusterExpansionZoom(f.properties.cluster_id, (err, zoom) => {
      if (err) return;
      map.easeTo({ center: f.geometry.coordinates, zoom });
    });
  });
}

/* ---------- Mapa do resultado ---------- */
window.SafeRoute.renderResultMap = function (containerId, dados) {
  if (!ensureToken()) return;
  const map = new mapboxgl.Map({
    container: containerId, style: currentStyle(),
    center: [(dados.origem.lon + dados.destino.lon) / 2,
             (dados.origem.lat + dados.destino.lat) / 2],
    zoom: 12,
  });
  map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');

  map.on('load', () => {
    // 3 rotas como linhas
    dados.rotas.forEach(r => {
      map.addSource('rota-' + r.id, {
        type: 'geojson',
        data: { type: 'Feature', geometry: { type: 'LineString', coordinates: r.geometria } },
      });
      map.addLayer({
        id: 'rota-' + r.id, type: 'line', source: 'rota-' + r.id,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': r.cor,
          'line-width': r.id === dados.recomendada ? 7 : 5,
          'line-opacity': r.id === dados.recomendada ? 1 : 0.7,
        },
      });
    });

    // Markers de origem/destino
    new mapboxgl.Marker({ color: '#10B981' })
      .setLngLat([dados.origem.lon, dados.origem.lat])
      .setPopup(new mapboxgl.Popup().setText('📍 Origem'))
      .addTo(map);
    new mapboxgl.Marker({ color: '#EF4444' })
      .setLngLat([dados.destino.lon, dados.destino.lat])
      .setPopup(new mapboxgl.Popup().setText('🚩 Destino'))
      .addTo(map);

    // Bounds
    const bounds = new mapboxgl.LngLatBounds()
      .extend([dados.origem.lon, dados.origem.lat])
      .extend([dados.destino.lon, dados.destino.lat]);
    map.fitBounds(bounds, { padding: 80, duration: 0 });
  });

  // Re-render no theme change
  new MutationObserver(() => map.setStyle(currentStyle()))
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  // Cards clicáveis destacam a rota
  document.querySelectorAll('.sr-route-card').forEach(card => {
    card.addEventListener('click', () => {
      const id = card.dataset.id;
      dados.rotas.forEach(r => {
        if (map.getLayer('rota-' + r.id)) {
          map.setPaintProperty('rota-' + r.id, 'line-width', r.id === id ? 8 : 4);
          map.setPaintProperty('rota-' + r.id, 'line-opacity', r.id === id ? 1 : 0.45);
        }
      });
    });
  });
};

/* ---------- Wiring de ações da tela de resultado ---------- */
window.SafeRoute.wireResultActions = function (dados) {
  // Deep link Google Maps
  const nav = document.getElementById('btnNavegar');
  if (nav) {
    const o = `${dados.origem.lat},${dados.origem.lon}`;
    const d = `${dados.destino.lat},${dados.destino.lon}`;
    nav.href = `https://www.google.com/maps/dir/?api=1&origin=${o}&destination=${d}`;
  }

  // Favoritar (Tarefa 4.4)
  document.getElementById('btnFavoritar')?.addEventListener('click', async () => {
    if (window.SR_CONFIG.isAuthenticated) {
      const r = await fetch('/api/favoritas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origem: dados.origem.endereco, destino: dados.destino.endereco,
          modo: dados.modo, prioridade: dados.prioridade,
        }),
      });
      if (r.ok) window.SafeRoute.toast('❤️ Salvo na sua conta!');
      else window.SafeRoute.toast('Erro ao salvar', 'error');
    } else {
      const fav = JSON.parse(localStorage.getItem('saferoute:favoritas') || '[]');
      fav.unshift({
        origem: dados.origem.endereco, destino: dados.destino.endereco,
        modo: dados.modo, prioridade: dados.prioridade, ts: Date.now(),
      });
      localStorage.setItem('saferoute:favoritas', JSON.stringify(fav.slice(0, 10)));
      window.SafeRoute.toast('❤️ Salvo neste navegador');
    }
  });

  // Compartilhar (Tarefa 2.6)
  document.getElementById('btnCompartilhar')?.addEventListener('click', async () => {
    const r = await fetch('/api/compartilhar-rota', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origem: dados.origem.endereco, destino: dados.destino.endereco,
        horario: dados.horario, prioridade: dados.prioridade, modo: dados.modo,
      }),
    });
    const j = await r.json();
    const url = window.location.origin + j.url;
    try {
      await navigator.clipboard.writeText(url);
      window.SafeRoute.toast('🔗 Link copiado!');
    } catch {
      prompt('Copie o link:', url);
    }
  });
};

/* ---------- Boot ---------- */
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('map')) initMainMap();
});
