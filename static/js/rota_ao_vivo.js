/* rota_ao_vivo.js — acompanhamento em tempo real do usuário sobre a rota.
 *
 * PARTE 3.1: radar aparece IMEDIATAMENTE no início da rota (linha[0]),
 *           sem esperar o GPS responder. Quando GPS chega, marker se move.
 * PARTE 3.2: HUD (#liveHUD) com distância restante + tempo estimado,
 *           atualizado a cada nova posição.
 */
window.SafeRoute = window.SafeRoute || {};

window.SafeRoute.startLiveRoute = function (map, dados) {
  if (!navigator.geolocation) {
    window.SafeRoute.toast('Geolocalização não disponível.', 'error');
    return null;
  }

  const recomendada = dados.rotas.find(r => r.id === dados.recomendada) || dados.rotas[0];
  const linha = recomendada.geometria; // [[lon,lat], ...]
  const destino = [dados.destino.lon, dados.destino.lat];

  // ─── Helpers de geometria ───
  function distMeters(a, b) {
    const R = 6371000;
    const toRad = d => d * Math.PI / 180;
    const dLat = toRad(b[1] - a[1]);
    const dLon = toRad(b[0] - a[0]);
    const lat1 = toRad(a[1]), lat2 = toRad(b[1]);
    const x = Math.sin(dLat / 2) ** 2 +
              Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }
  function distToLine(point, polyline) {
    let min = Infinity;
    for (let i = 0; i < polyline.length - 1; i++) {
      const segDist = pointToSegment(point, polyline[i], polyline[i + 1]);
      if (segDist < min) min = segDist;
    }
    return min;
  }
  function pointToSegment(p, a, b) {
    const ax = a[0], ay = a[1], bx = b[0], by = b[1], px = p[0], py = p[1];
    const dx = bx - ax, dy = by - ay;
    if (dx === 0 && dy === 0) return distMeters(p, a);
    const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
    return distMeters(p, [ax + t * dx, ay + t * dy]);
  }
  // Calcula distância restante na rota a partir do ponto mais próximo
  function distanciaRestante(currentPoint, polyline) {
    // Acha índice do segmento mais próximo
    let minIdx = 0, minDist = Infinity;
    for (let i = 0; i < polyline.length - 1; i++) {
      const d = pointToSegment(currentPoint, polyline[i], polyline[i + 1]);
      if (d < minDist) { minDist = d; minIdx = i; }
    }
    // Distância do ponto até o fim do segmento atual + segmentos restantes + destino
    let total = distMeters(currentPoint, polyline[minIdx + 1]);
    for (let i = minIdx + 1; i < polyline.length - 1; i++) {
      total += distMeters(polyline[i], polyline[i + 1]);
    }
    return total;
  }
  function fmtDist(m) {
    return m < 1000 ? Math.round(m) + ' m' : (m / 1000).toFixed(1) + ' km';
  }
  function fmtMin(min) {
    if (min < 1) return '< 1 min';
    if (min < 60) return Math.round(min) + ' min';
    const h = Math.floor(min / 60), mm = Math.round(min % 60);
    return h + 'h' + (mm ? mm + 'min' : '');
  }

  // Velocidade estimada por modo (km/h)
  const velKmh = {
    ape: 5, bicicleta: 15, carro: 30, transporte_publico: 20,
  }[dados.modo] || 10;

  // ─── PARTE 3.1: Cria marker IMEDIATAMENTE na origem da rota (linha[0]) ───
  const startPos = linha[0] || [dados.origem.lon, dados.origem.lat];
  const el = document.createElement('div');
  el.className = 'sr-livepin sr-livepin-loading';
  el.innerHTML = `
    <span class="sr-radar-sweep"></span>
    <span class="sr-livepin-pulse"></span>
    <span class="sr-livepin-pulse sr-livepin-pulse-2"></span>
    <span class="sr-livepin-dot"></span>
  `;
  let userMarker = new maplibregl.Marker({ element: el }).setLngLat(startPos).addTo(map);
  map.easeTo({ center: startPos, zoom: 16, duration: 600 });

  // ─── PARTE 3.2: Cria HUD com info da rota ───
  let hud = document.getElementById('liveHUD');
  if (!hud) {
    hud = document.createElement('div');
    hud.id = 'liveHUD';
    hud.className = 'sr-livehud';
    document.body.appendChild(hud);
  }
  let speedLimit = null;  // Item #2 — última leitura
  function renderHUD({ buscando, distRest, tempoMin, foraDaRota } = {}) {
    if (buscando) {
      hud.innerHTML = `
        <div class="sr-livehud-row">
          <span class="sr-livehud-label">📡 Procurando GPS…</span>
        </div>
        <div class="sr-livehud-row sr-livehud-mute">
          Aponte para a origem da rota recomendada.
        </div>`;
      return;
    }
    const speedHTML = speedLimit
      ? `<div class="sr-speedbadge"><strong>${speedLimit}</strong><span>km/h</span></div>`
      : '';
    hud.innerHTML = `
      <div class="sr-livehud-stats">
        <div class="sr-livehud-stat">
          <strong>${fmtDist(distRest)}</strong>
          <span>restante</span>
        </div>
        <div class="sr-livehud-stat">
          <strong>${fmtMin(tempoMin)}</strong>
          <span>estimado</span>
        </div>
        ${speedHTML}
      </div>
      ${foraDaRota
        ? `<div class="sr-livehud-warn">⚠️ Você se afastou da rota</div>`
        : `<div class="sr-livehud-ok">✅ Você está no caminho</div>`}
    `;
  }
  renderHUD({ buscando: true });

  // Busca speed limit a cada ~30s (não a cada update GPS pra não sobrecarregar Overpass)
  let lastSpeedFetch = 0;

  // ─── watchPosition ───
  let lastAlertTs = 0;
  let arrived = false;

  function alertaRateLimited(msg, kind) {
    const now = Date.now();
    if (now - lastAlertTs < 8000) return;
    lastAlertTs = now;
    window.SafeRoute.toast(msg, kind);
    if (window.navigator.vibrate) window.navigator.vibrate(120);
  }

  const id = navigator.geolocation.watchPosition((pos) => {
    if (arrived) return;
    const u = [pos.coords.longitude, pos.coords.latitude];

    // Move marker e remove estado loading
    el.classList.remove('sr-livepin-loading');
    userMarker.setLngLat(u);

    const dRota = distToLine(u, linha);
    const foraDaRota = dRota > 100;
    const distRest = distanciaRestante(u, linha);
    const tempoMin = (distRest / 1000) / velKmh * 60;

    renderHUD({ distRest, tempoMin, foraDaRota });

    // Item #2 — busca speed limit a cada 30s
    if (Date.now() - lastSpeedFetch > 30000 && window.SafeRoute.fetchSpeedLimit) {
      lastSpeedFetch = Date.now();
      window.SafeRoute.fetchSpeedLimit(u[1], u[0]).then(lim => {
        if (lim) { speedLimit = lim; renderHUD({ distRest, tempoMin, foraDaRota }); }
      });
    }

    if (foraDaRota) {
      alertaRateLimited('⚠️ Você está fora da rota recomendada (>100m).', 'error');
    }

    const dDest = distMeters(u, destino);
    if (dDest < 50) {
      arrived = true;
      hud.innerHTML = `<div class="sr-livehud-arrived">🎉 Você chegou ao destino!</div>`;
      window.SafeRoute.toast('🎉 Você chegou ao destino!', 'success');
      navigator.geolocation.clearWatch(id);
    }
  }, (err) => {
    window.SafeRoute.toast('Erro de geolocalização: ' + err.message, 'error');
    renderHUD({ buscando: true });
  }, {
    enableHighAccuracy: true, maximumAge: 5000, timeout: 15000,
  });

  return {
    stop() {
      navigator.geolocation.clearWatch(id);
      userMarker?.remove();
      hud?.remove();
    }
  };
};
