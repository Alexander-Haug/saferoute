/* sos.js — botão SOS de emergência.
 * Modal com 3 opções: 190 (PM), 192 (SAMU), 193 (Bombeiros).
 * + Compartilhar localização atual via WhatsApp ou copiar link.
 *
 * O botão é injetado em qualquer página com #map ou #resultMap.
 */
(function () {
  function inject() {
    // Evita duplicar se já existe
    if (document.getElementById('sosFab')) return;
    // Só injeta se tem mapa nesta página
    if (!document.getElementById('map') && !document.getElementById('resultMap')) return;

    const btn = document.createElement('button');
    btn.id = 'sosFab';
    btn.className = 'sr-fab-sos';
    btn.setAttribute('aria-label', 'Emergência SOS');
    btn.title = 'SOS — Emergência';
    btn.innerHTML = '<span class="sr-fab-sos-text">SOS</span>';
    document.body.appendChild(btn);

    btn.addEventListener('click', openModal);
  }

  function openModal() {
    const back = document.createElement('div');
    back.className = 'sr-modal-backdrop';
    back.innerHTML = `
      <div class="sr-modal sr-sos-modal" role="dialog" aria-labelledby="sosTitle">
        <header class="sr-sos-head">
          <h2 id="sosTitle">🚨 Emergência</h2>
          <button class="sr-iconbtn sr-modal-close" aria-label="Fechar">✕</button>
        </header>
        <p class="sr-muted">Em caso de risco imediato, acione um dos serviços abaixo.
           As chamadas são <strong>gratuitas</strong>.</p>

        <div class="sr-sos-options">
          <a href="tel:190" class="sr-sos-btn sr-sos-btn-policia">
            <span class="sr-sos-emoji">👮</span>
            <strong>190</strong>
            <span>Polícia Militar</span>
          </a>
          <a href="tel:192" class="sr-sos-btn sr-sos-btn-samu">
            <span class="sr-sos-emoji">🚑</span>
            <strong>192</strong>
            <span>SAMU</span>
          </a>
          <a href="tel:193" class="sr-sos-btn sr-sos-btn-bombeiros">
            <span class="sr-sos-emoji">🚒</span>
            <strong>193</strong>
            <span>Bombeiros</span>
          </a>
        </div>

        <div class="sr-sos-share">
          <p class="sr-mini sr-muted">Compartilhe sua localização atual:</p>
          <div class="sr-result-actions-row">
            <button id="sosShareWhats" class="sr-btn sr-btn-success sr-btn-pill">
              📱 WhatsApp
            </button>
            <button id="sosShareCopy" class="sr-btn sr-btn-ghost sr-btn-pill">
              📋 Copiar link
            </button>
          </div>
        </div>

        <p class="sr-mini sr-muted" style="text-align:center; margin-top: 12px;">
          ⚠️ Use só em emergências reais. Trote é crime.
        </p>
      </div>
    `;
    document.body.appendChild(back);

    function close() { back.remove(); }
    back.querySelector('.sr-modal-close').addEventListener('click', close);
    back.addEventListener('click', (e) => { if (e.target === back) close(); });
    document.addEventListener('keydown', escClose);
    function escClose(e) { if (e.key === 'Escape') { close(); document.removeEventListener('keydown', escClose); } }

    // Compartilhar
    document.getElementById('sosShareWhats').addEventListener('click', () => share('whats'));
    document.getElementById('sosShareCopy').addEventListener('click', () => share('copy'));

    function share(via) {
      if (!navigator.geolocation) {
        window.SafeRoute.toast('Geolocalização não disponível.', 'error');
        return;
      }
      window.SafeRoute.toast('📡 Pegando sua localização…');
      navigator.geolocation.getCurrentPosition((pos) => {
        const { latitude: lat, longitude: lon } = pos.coords;
        const url = `https://www.google.com/maps?q=${lat},${lon}`;
        const msg = `🆘 ESTOU PRECISANDO DE AJUDA!\nEstou aqui: ${url}\n(via SafeRoute)`;
        if (via === 'whats') {
          // wa.me sem número específico — abre seletor de contato no WhatsApp
          window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, '_blank');
        } else {
          navigator.clipboard.writeText(msg)
            .then(() => window.SafeRoute.toast('📋 Link copiado!'))
            .catch(() => prompt('Copie:', msg));
        }
      }, (err) => {
        window.SafeRoute.toast('Erro ao obter localização: ' + err.message, 'error');
      }, { enableHighAccuracy: true, timeout: 8000 });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
})();
