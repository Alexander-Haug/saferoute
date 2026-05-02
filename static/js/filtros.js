/* filtros.js — chips clicáveis pra filtrar o mapa (Tarefa 2.4). */
(function () {
  const cards = document.querySelectorAll('.sr-chip[data-filter]');
  const clear = document.getElementById('clearFilter');

  function setActive(filter) {
    cards.forEach(c => c.classList.toggle('is-active', c.dataset.filter === filter));
    if (window.SafeRoute && window.SafeRoute._setMapFilter) {
      window.SafeRoute._setMapFilter(filter);
    }
  }

  cards.forEach(c => c.addEventListener('click', () => setActive(c.dataset.filter)));
  clear?.addEventListener('click', () => setActive('all'));
})();
