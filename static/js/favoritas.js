/* favoritas.js — Tarefa 4.4
 * Lê favoritas do servidor (se logado) ou localStorage (convidado)
 * e renderiza no #favList do app.
 */
(function () {
  const list = document.getElementById('favList');
  if (!list) return;

  function render(items) {
    if (!items.length) {
      list.innerHTML = '<li class="sr-muted">Nenhuma rota salva ainda.</li>';
      return;
    }
    list.innerHTML = items.slice(0, 5).map(it => `
      <li class="sr-fav-row">
        <a href="/app/rota/resultado?origem=${encodeURIComponent(it.origem)}&destino=${encodeURIComponent(it.destino)}&modo=${it.modo || 'ape'}&prioridade=${it.prioridade || 'equilibrada'}">
          <strong>${it.nome || (it.origem + ' → ' + it.destino)}</strong>
          ${it.nome ? `<span class="sr-mini sr-muted">${it.origem} → ${it.destino}</span>` : ''}
        </a>
      </li>
    `).join('');
  }

  if (window.SR_CONFIG && window.SR_CONFIG.isAuthenticated) {
    fetch('/api/favoritas').then(r => r.json()).then(render).catch(() => render([]));
  } else {
    const local = JSON.parse(localStorage.getItem('saferoute:favoritas') || '[]');
    render(local);
  }
})();
