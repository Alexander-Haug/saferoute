/* app.js — orquestra interações da tela /app:
 * - Tarefa 2.2: toggle "Agora vs Depois" sincroniza o datetime.
 * - Tarefa 2.3: lembra modo + prioridade no localStorage.
 * - Salva no histórico local quando convidado.
 */
(function () {
  const form = document.getElementById('routeForm');
  if (!form) return;

  const horario = document.getElementById('horarioInput');
  const radios = form.querySelectorAll('input[name="quando"]');

  function applyQuando() {
    const v = form.quando.value;
    if (v === 'agora') {
      const tz = new Intl.DateTimeFormat('sv-SE', {
        timeZone: 'America/Sao_Paulo',
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false,
      });
      const parts = tz.formatToParts(new Date()).reduce((a, p) => (a[p.type] = p.value, a), {});
      horario.value = `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
      horario.disabled = true;
    } else {
      horario.disabled = false;
    }
    sessionStorage.setItem('saferoute:quando', v);
  }
  radios.forEach(r => r.addEventListener('change', applyQuando));
  const saved = sessionStorage.getItem('saferoute:quando');
  if (saved) {
    const r = form.querySelector(`input[name="quando"][value="${saved}"]`);
    if (r) r.checked = true;
  }
  applyQuando();

  // Item #3 — mostra hint quando modo "transporte_publico" é escolhido
  const modoHint = document.getElementById('modoHint');
  if (modoHint) {
    function syncHint() {
      const modoVal = (form.querySelector('input[name="modo"]:checked') || {}).value;
      modoHint.hidden = modoVal !== 'transporte_publico';
    }
    form.querySelectorAll('input[name="modo"]').forEach(r => r.addEventListener('change', syncHint));
    syncHint();
  }

  // Persistir modo + prioridade
  const KEY_PREFS = 'saferoute:prefs';
  try {
    const prefs = JSON.parse(localStorage.getItem(KEY_PREFS) || '{}');
    if (prefs.modo) {
      const m = form.querySelector(`input[name="modo"][value="${prefs.modo}"]`);
      if (m) m.checked = true;
    }
    if (prefs.prioridade) {
      const p = form.querySelector(`input[name="prioridade"][value="${prefs.prioridade}"]`);
      if (p) p.checked = true;
    }
  } catch {}

  // Bônus: pré-preenche origem/destino da última busca (persistência)
  try {
    const last = JSON.parse(localStorage.getItem('saferoute:lastRoute') || 'null');
    if (last) {
      if (!form.origem.value && last.origem) form.origem.value = last.origem;
      if (!form.destino.value && last.destino) form.destino.value = last.destino;
      if (last.modo) {
        const r = form.querySelector(`input[name="modo"][value="${last.modo}"]`);
        if (r) r.checked = true;
      }
      if (last.prioridade) {
        const r = form.querySelector(`input[name="prioridade"][value="${last.prioridade}"]`);
        if (r) r.checked = true;
      }
    }
  } catch {}

  form.addEventListener('submit', (ev) => {
    // Bug 5: validação prévia
    const o = form.origem.value.trim();
    const d = form.destino.value.trim();
    if (o.length < 5) {
      ev.preventDefault();
      window.SafeRoute.toast('Origem precisa ter pelo menos 5 caracteres.', 'error');
      form.origem.focus();
      return;
    }
    if (d.length < 5) {
      ev.preventDefault();
      window.SafeRoute.toast('Destino precisa ter pelo menos 5 caracteres.', 'error');
      form.destino.focus();
      return;
    }

    const prefs = {
      modo: form.modo.value, prioridade: form.prioridade.value,
    };
    localStorage.setItem(KEY_PREFS, JSON.stringify(prefs));

    // Bônus: salva última rota completa pra persistência ao voltar
    localStorage.setItem('saferoute:lastRoute', JSON.stringify({
      origem: form.origem.value, destino: form.destino.value,
      modo: form.modo.value, prioridade: form.prioridade.value,
      ts: Date.now(),
    }));

    // Histórico local (só convidado)
    if (!window.SR_CONFIG.isAuthenticated) {
      const h = JSON.parse(localStorage.getItem('saferoute:historico') || '[]');
      h.unshift({
        origem: form.origem.value, destino: form.destino.value,
        modo: form.modo.value, prioridade: form.prioridade.value,
        ts: Date.now(),
      });
      localStorage.setItem('saferoute:historico', JSON.stringify(h.slice(0, 30)));
    }
  });
})();
