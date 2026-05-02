/* geolocation.js — Tarefa 2.1
 * Botão 📍 → navigator.geolocation → reverse geocode → preenche origem.
 */
(function () {
  const btn = document.getElementById('geoBtn');
  const input = document.getElementById('origemInput');
  if (!btn || !input) return;

  btn.addEventListener('click', () => {
    if (!navigator.geolocation) {
      window.SafeRoute.toast('Geolocalização não disponível.', 'error');
      return;
    }
    btn.disabled = true; const orig = btn.textContent; btn.textContent = '…';
    navigator.geolocation.getCurrentPosition(async (pos) => {
      try {
        const { latitude, longitude } = pos.coords;
        const r = await fetch(`/api/reverse-geocode?lat=${latitude}&lon=${longitude}`);
        const j = await r.json();
        input.value = j.endereco || `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
        window.SafeRoute.toast('📍 Localização atual preenchida');
      } catch {
        window.SafeRoute.toast('Erro ao obter endereço.', 'error');
      } finally {
        btn.disabled = false; btn.textContent = orig;
      }
    }, () => {
      window.SafeRoute.toast('Permissão de localização negada.', 'error');
      btn.disabled = false; btn.textContent = orig;
    }, { enableHighAccuracy: true, timeout: 10000 });
  });
})();
