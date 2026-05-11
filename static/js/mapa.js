/* mapa.js — integração Mapbox GL JS.
 * Mostra heatmap + cluster de ocorrências (app.html) e
 * desenha 3 rotas no resultado.
 */
window.SafeRoute = window.SafeRoute || {};

const SP_CENTER = [-46.6333, -23.5505];
// Estilos com MAIS nomes de lugares (bairros, parques, pontos comerciais),
// não só endereços. streets-v12 = referência, navigation-night = bom contraste no escuro.
// PARTE 3.3: estilos com bons rótulos de lugares.
// streets-v12 (claro) + dark-v11 (escuro) — ambos têm POIs (parques, shoppings, restaurantes).
const STYLE_LIGHT = 'mapbox://styles/mapbox/streets-v12';
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
  let currentView = 'clusters';   // 'clusters' | 'heatmap'
  let currentHour = null;          // null = sem filtro de hora; 0-23 = filtra
  let trafficVisible = false;

  map.on('load', async () => {
    document.getElementById('mapSkeleton')?.classList.add('is-hidden');
    setTimeout(() => document.getElementById('mapSkeleton')?.remove(), 400);
    await loadOccurrences(map, currentFilter);
    addTrafficLayer(map);  // Item #4 — disponível via toggle
    try { geolocate.trigger(); } catch {}

    // Toggle clusters/heatmap (não mexe no botão de tráfego)
    document.querySelectorAll('#viewModeToggle .sr-vm-btn[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#viewModeToggle .sr-vm-btn[data-view]')
                .forEach(b => b.classList.toggle('is-active', b === btn));
        currentView = btn.dataset.view;
        applyView(map, currentView);
      });
    });

    // Toggle tráfego (independente)
    const trafficBtn = document.getElementById('trafficToggle');
    trafficBtn?.addEventListener('click', () => {
      const on = window.SafeRoute._toggleTraffic(map);
      trafficBtn.classList.toggle('is-active', on);
    });

    // Slider de hora — filtra ocorrências mostradas no mapa
    const range = document.getElementById('hourRange');
    const label = document.getElementById('hourLabel');
    const reset = document.getElementById('hourReset');
    range?.addEventListener('input', () => {
      currentHour = parseInt(range.value, 10);
      label.textContent = currentHour + 'h';
      applyHourFilter(map, currentHour);
    });
    reset?.addEventListener('click', () => {
      currentHour = null;
      range.value = 12; label.textContent = '12h';
      applyHourFilter(map, null);
    });
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

  // Hover em cluster → mostra popup com bairros principais
  let clusterHoverPopup = null;
  map.on('mouseenter', 'oc-clusters', () => map.getCanvas().style.cursor = 'pointer');
  map.on('mouseleave', 'oc-clusters', () => {
    map.getCanvas().style.cursor = '';
    clusterHoverPopup?.remove(); clusterHoverPopup = null;
  });
  map.on('mousemove', 'oc-clusters', (e) => {
    const f = e.features[0];
    const cid = f.properties.cluster_id;
    map.getSource(SRC).getClusterLeaves(cid, 100, 0, (err, leaves) => {
      if (err || !leaves) return;
      // agrega por bairro/tipo
      const bairros = {};
      let totalQtd = 0;
      leaves.forEach(l => {
        const b = l.properties.bairro;
        bairros[b] = (bairros[b] || 0) + (l.properties.qtd || 1);
        totalQtd += l.properties.qtd || 1;
      });
      const top = Object.entries(bairros).sort((a, b) => b[1] - a[1]).slice(0, 3);
      const html = `
        <div class="sr-popup">
          <strong class="sr-popup-title">📍 ${f.properties.point_count_abbreviated} pontos</strong>
          <div class="sr-popup-row">${totalQtd} ocorrências no total</div>
          <div class="sr-popup-mute">Bairros principais:</div>
          ${top.map(([b, n]) => `<div class="sr-popup-row">• ${b}: <strong>${n}</strong></div>`).join('')}
        </div>`;
      clusterHoverPopup?.remove();
      clusterHoverPopup = new mapboxgl.Popup({
        closeButton: false, closeOnClick: false, maxWidth: '240px', offset: 12,
      }).setLngLat(f.geometry.coordinates).setHTML(html).addTo(map);
    });
  });
}

// Item #8 — Carrega radares (OSM speed_camera) ao longo da rota
async function loadRadaresParaRota(map, geometria, bounds) {
  // bbox da rota: minLat,minLon,maxLat,maxLon
  const sw = bounds.getSouthWest();
  const ne = bounds.getNorthEast();
  const bboxParam = `${sw.lat},${sw.lng},${ne.lat},${ne.lng}`;
  try {
    const r = await fetch(`/api/radares?bbox=${encodeURIComponent(bboxParam)}`);
    if (!r.ok) return;
    const data = await r.json();
    const radares = data.radares || [];
    if (!radares.length) return;

    map.addSource('radares', {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: radares.map(rad => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [rad.lon, rad.lat] },
          properties: { limite: rad.limite, tipo: rad.tipo },
        })),
      },
    });
    map.addLayer({
      id: 'radares-layer',
      type: 'circle',
      source: 'radares',
      paint: {
        'circle-radius': 8,
        'circle-color': '#7C3AED',
        'circle-stroke-width': 2,
        'circle-stroke-color': '#fff',
      },
    });
    // Texto "📷" sobre o ponto
    map.addLayer({
      id: 'radares-icon',
      type: 'symbol', source: 'radares',
      layout: { 'text-field': '📷', 'text-size': 12, 'text-allow-overlap': true },
    });

    map.on('click', 'radares-layer', (e) => {
      const f = e.features[0];
      new mapboxgl.Popup({ closeButton: false })
        .setLngLat(f.geometry.coordinates)
        .setHTML(`
          <div class="sr-popup">
            <strong class="sr-popup-title">📷 Radar</strong>
            <div class="sr-popup-row">Velocidade limite: <strong>${f.properties.limite || '?'} km/h</strong></div>
            <div class="sr-popup-mute">Tipo: ${f.properties.tipo}</div>
          </div>
        `).addTo(map);
    });
    map.on('mouseenter', 'radares-layer', () => map.getCanvas().style.cursor = 'pointer');
    map.on('mouseleave', 'radares-layer', () => map.getCanvas().style.cursor = '');
  } catch (e) {
    console.warn('[SafeRoute] radares falhou:', e);
  }
}

// Item #2 — Badge de limite de velocidade durante navegação ao vivo
window.SafeRoute.fetchSpeedLimit = async function (lat, lon) {
  try {
    const r = await fetch(`/api/speed-limit?lat=${lat}&lon=${lon}`);
    if (!r.ok) return null;
    const j = await r.json();
    return j.limite;  // pode ser null se OSM não tem dado pra via
  } catch { return null; }
};

// Item #4 — Camada de trânsito Mapbox (vetor, atualização ~5min)
function addTrafficLayer(map) {
  if (map.getSource('mapbox-traffic')) return;
  map.addSource('mapbox-traffic', {
    type: 'vector',
    url: 'mapbox://mapbox.mapbox-traffic-v1',
  });
  // Adiciona camada com visibility=none — usuário liga via botão
  map.addLayer({
    id: 'traffic-line',
    type: 'line',
    source: 'mapbox-traffic',
    'source-layer': 'traffic',
    layout: { 'visibility': 'none', 'line-cap': 'round' },
    paint: {
      'line-width': 2.5,
      'line-color': [
        'match', ['get', 'congestion'],
        'low', '#10B981',
        'moderate', '#F59E0B',
        'heavy', '#EF4444',
        'severe', '#7F1D1D',
        'transparent',
      ],
    },
  });
}
window.SafeRoute._toggleTraffic = (map) => {
  if (!map.getLayer('traffic-line')) return false;
  const v = map.getLayoutProperty('traffic-line', 'visibility');
  const next = v === 'visible' ? 'none' : 'visible';
  map.setLayoutProperty('traffic-line', 'visibility', next);
  return next === 'visible';
};

// Toggle no mapa do resultado pra esconder/mostrar ocorrências
function addResultMapToggle(map) {
  const wrap = document.querySelector('.sr-result-map') || document.getElementById('resultMap')?.parentNode;
  if (!wrap) return;
  const btn = document.createElement('button');
  btn.className = 'sr-result-toggle';
  btn.innerHTML = '👁️ Ocorrências';
  btn.title = 'Mostrar/esconder pontos de ocorrência';
  let visible = true;
  btn.addEventListener('click', () => {
    visible = !visible;
    const v = visible ? 'visible' : 'none';
    ['oc-heat', 'oc-clusters', 'oc-cluster-count', 'oc-points'].forEach(l => {
      if (map.getLayer(l)) map.setLayoutProperty(l, 'visibility', v);
    });
    btn.innerHTML = visible ? '👁️ Ocorrências' : '👁️‍🗨️ Mostrar';
    btn.classList.toggle('is-off', !visible);
  });
  wrap.appendChild(btn);
}

// Alterna entre modo clusters (com números) e heatmap puro
function applyView(map, mode) {
  const layers = ['oc-clusters', 'oc-cluster-count', 'oc-points'];
  layers.forEach(l => {
    if (map.getLayer(l)) {
      map.setLayoutProperty(l, 'visibility', mode === 'clusters' ? 'visible' : 'none');
    }
  });
  if (map.getLayer('oc-heat')) {
    // heatmap fica mais opaco quando é o modo principal
    map.setPaintProperty('oc-heat', 'heatmap-opacity',
      mode === 'heatmap'
        ? ['interpolate', ['linear'], ['zoom'], 7, 1, 15, 0.7]
        : ['interpolate', ['linear'], ['zoom'], 7, 0.85, 15, 0.4]);
  }
}

// Filtra pontos visíveis pela hora (slider). null = sem filtro.
function applyHourFilter(map, hour) {
  const SRC = 'ocorrencias';
  if (!map.getLayer('oc-points')) return;
  if (hour === null || hour === undefined) {
    map.setFilter('oc-points', ['!', ['has', 'point_count']]);
    map.setFilter('oc-clusters', ['has', 'point_count']);
  } else {
    // Mostra ocorrências com hora dentro de janela ±1
    const lo = (hour + 23) % 24;
    const hi = (hour + 1) % 24;
    const filter = ['all',
      ['!', ['has', 'point_count']],
      ['any',
        ['==', ['get', 'hora'], hour],
        ['==', ['get', 'hora'], lo],
        ['==', ['get', 'hora'], hi],
      ]
    ];
    map.setFilter('oc-points', filter);
    // clusters não suportam filtro pós-cluster facilmente — escondemos
    map.setLayoutProperty('oc-clusters', 'visibility', 'none');
    map.setLayoutProperty('oc-cluster-count', 'visibility', 'none');
  }
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

  map.on('load', async () => {
    // PRIMEIRO: ocorrências (bolinhas coloridas) — fica como camada de fundo
    // pra usuário ver onde estão pontos importantes em volta da rota.
    await loadOccurrences(map, 'all');

    // Heatmap mais sutil pra não competir com as rotas
    if (map.getLayer('oc-heat')) {
      map.setPaintProperty('oc-heat', 'heatmap-opacity',
        ['interpolate', ['linear'], ['zoom'], 7, 0.5, 15, 0.25]);
    }

    // DEPOIS: 3 rotas como linhas POR CIMA das ocorrências
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

    // Garante que rotas fiquem acima de heatmap/clusters
    ['rota-A', 'rota-B', 'rota-C'].forEach(id => {
      if (map.getLayer(id)) map.moveLayer(id);
    });

    // Markers de origem/destino — sempre por último (em cima de tudo)
    new mapboxgl.Marker({ color: '#10B981' })
      .setLngLat([dados.origem.lon, dados.origem.lat])
      .setPopup(new mapboxgl.Popup().setText('📍 Origem'))
      .addTo(map);
    new mapboxgl.Marker({ color: '#EF4444' })
      .setLngLat([dados.destino.lon, dados.destino.lat])
      .setPopup(new mapboxgl.Popup().setText('🚩 Destino'))
      .addTo(map);

    // Bounds englobando origem, destino E a polyline da recomendada
    const bounds = new mapboxgl.LngLatBounds()
      .extend([dados.origem.lon, dados.origem.lat])
      .extend([dados.destino.lon, dados.destino.lat]);
    const rec = dados.rotas.find(r => r.id === dados.recomendada);
    if (rec) rec.geometria.forEach(c => bounds.extend(c));
    map.fitBounds(bounds, { padding: 80, duration: 0 });

    // Toggle pra esconder/mostrar ocorrências no mapa do resultado
    addResultMapToggle(map);

    // Item #8 — radares ao longo de toda a rota (não só perto)
    if (rec) {
      loadRadaresParaRota(map, rec.geometria, bounds);
    }
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

  return map;
};

/* ---------- Wiring de ações da tela de resultado ---------- */
window.SafeRoute.wireResultActions = function (dados, mapInstance) {
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

  // Rota ao vivo
  let liveSession = null;
  const btnAoVivo = document.getElementById('btnAoVivo');
  btnAoVivo?.addEventListener('click', () => {
    if (liveSession) {
      liveSession.stop(); liveSession = null;
      btnAoVivo.textContent = '📡 Acompanhar rota ao vivo';
      btnAoVivo.classList.remove('is-active');
      window.SafeRoute.toast('Acompanhamento encerrado.');
      return;
    }
    if (!mapInstance) { window.SafeRoute.toast('Mapa não carregado.', 'error'); return; }
    liveSession = window.SafeRoute.startLiveRoute(mapInstance, dados);
    if (liveSession) {
      btnAoVivo.innerHTML = '⏹️ Parar acompanhamento';
      btnAoVivo.classList.add('is-active');
      window.SafeRoute.toast('📡 Acompanhamento ao vivo iniciado.');
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
