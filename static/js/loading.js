/* loading.js — feedback visual durante submit do formulário (Tarefa 4.2). */
(function () {
  const form = document.getElementById('routeForm');
  if (!form) return;
  const btn = form.querySelector('button[type="submit"]');
  if (!btn) return;
  const originalLabel = btn.innerHTML;

  form.addEventListener('submit', () => {
    btn.disabled = true;
    btn.innerHTML = `<span class="sr-spinner" aria-hidden="true"></span>
                     Calculando rotas seguras… analisando 15 mil ocorrências`;
    setTimeout(() => {
      // Em caso de back/forward cache, restaura o botão
      btn.disabled = false;
      btn.innerHTML = originalLabel;
    }, 30000);
  });

  // Spinner CSS injetado uma vez
  if (!document.getElementById('sr-spinner-style')) {
    const s = document.createElement('style');
    s.id = 'sr-spinner-style';
    s.textContent = `
      .sr-spinner {
        display: inline-block; width: 16px; height: 16px;
        border: 2px solid rgba(255,255,255,.4);
        border-top-color: #fff; border-radius: 50%;
        animation: sr-spin .8s linear infinite; margin-right: 8px;
        vertical-align: -3px;
      }
      @keyframes sr-spin { to { transform: rotate(360deg); } }
    `;
    document.head.appendChild(s);
  }
})();

/* Helper global de toast */
window.SafeRoute = window.SafeRoute || {};
window.SafeRoute.toast = function (msg, kind) {
  const c = document.getElementById('toastContainer');
  if (!c) return;
  const t = document.createElement('div');
  t.className = 'sr-toast ' + (kind === 'error' ? 'sr-toast-error' : '');
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3200);
};
