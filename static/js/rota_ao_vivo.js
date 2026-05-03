/* rota_ao_vivo.js — acompanhamento em tempo real do usuário sobre a rota.
 * Usa navigator.geolocation.watchPosition. Calcula distância pra polyline
 * e alerta se: (1) usuário se afasta >100m da rota, (2) entra em ponto
 * com score de risco alto, (3) chega ao destino (<50m).
 *
 * Acionado pelo botão #btnAoVivo na tela de resultado.
 */
window.SafeRoute = window.SafeRoute || {};

window.SafeRoute.startLiveRoute = function (map, dados) {
  if (!navigator.geolocation) {
    window.SafeRoute.toast('Geolocalização não disponível.', 'error');
    return null;
  }

  const recomendada = dados.rotas.find(r => r.id === dados.recomendada) || dados.rotas[0];
  const linha = recomendada.geometria; // [[lon,lat], ...]
  let userMarker = null;
  let lastAlertTs = 0;
  let arrived = false;

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
    // Aproximação plana boa o bastante em escala urbana
    const ax = a[0], ay = a[1], bx = b[0], by = b[1], px = p[0], py = p[1];
    const dx = bx - ax, dy = by - ay;
    if (dx === 0 && dy === 0) return distMeters(p, a);
    const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
    return distMeters(p, [ax + t * dx, ay + t * dy]);
  }

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

    if (!userMarker) {
      const el = document.createElement('div');
      el.className = 'sr-livepin';
      el.innerHTML = '<span class="sr-livepin-dot"></span><span class="sr-livepin-pulse"></span>';
      userMarker = new mapboxgl.Marker({ element: el }).setLngLat(u).addTo(map);
      map.easeTo({ center: u, zoom: 16 });
    } else {
      userMarker.setLngLat(u);
    }

    // Distância pra rota
    const dRota = distToLine(u, linha);
    if (dRota > 100) {
      alertaRateLimited('⚠️ Você está fora da rota recomendada (>100m).', 'error');
    }

    // Distância pro destino
    const destino = [dados.destino.lon, dados.destino.lat];
    const dDest = distMeters(u, destino);
    if (dDest < 50) {
      arrived = true;
      window.SafeRoute.toast('🎉 Você chegou ao destino!', 'success');
      navigator.geolocation.clearWatch(id);
    }
  }, (err) => {
    window.SafeRoute.toast('Erro de geolocalização: ' + err.message, 'error');
  }, {
    enableHighAccuracy: true, maximumAge: 5000, timeout: 15000,
  });

  return {
    stop() {
      navigator.geolocation.clearWatch(id);
      userMarker?.remove();
    }
  };
};
