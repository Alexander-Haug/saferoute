/* autocomplete.js — sugestões de endereço com debounce e teclado.
 * Anexa a qualquer input com data-autocomplete="endereco".
 * Sugestões vêm de /api/suggest (Mapbox Geocoding com bbox SP).
 */
(function () {
  const DEBOUNCE_MS = 220;
  const MIN_CHARS = 3;

  function attach(input) {
    if (input._autoAttached) return;
    input._autoAttached = true;

    // Wrapper com posição relativa pra ancorar o dropdown
    const wrap = document.createElement('div');
    wrap.className = 'sr-ac-wrap';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    const dropdown = document.createElement('ul');
    dropdown.className = 'sr-ac-dropdown';
    dropdown.setAttribute('role', 'listbox');
    dropdown.hidden = true;
    wrap.appendChild(dropdown);

    let timer = null;
    let activeIdx = -1;
    let items = [];
    let lastQuery = '';
    let aborter = null;

    function close() {
      dropdown.hidden = true;
      activeIdx = -1;
    }

    function render() {
      if (!items.length) { close(); return; }
      dropdown.innerHTML = items.map((it, i) => `
        <li role="option" data-i="${i}"
            class="sr-ac-item ${i === activeIdx ? 'is-active' : ''}">
          <span class="sr-ac-pin">📍</span>
          <span class="sr-ac-label">
            <strong>${escapeHTML(it.text || it.label.split(',')[0])}</strong>
            <span>${escapeHTML(it.label)}</span>
          </span>
        </li>
      `).join('');
      dropdown.hidden = false;
    }

    function pick(it) {
      input.value = it.label;
      lastQuery = it.label;
      input.dataset.lat = it.lat;
      input.dataset.lon = it.lon;
      close();
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    async function fetchSuggestions(q) {
      if (aborter) aborter.abort();
      aborter = new AbortController();
      try {
        const r = await fetch('/api/suggest?q=' + encodeURIComponent(q),
                              { signal: aborter.signal });
        if (!r.ok) return;
        items = await r.json();
        activeIdx = -1;
        render();
      } catch (e) { /* aborted ou network */ }
    }

    input.setAttribute('autocomplete', 'off');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('role', 'combobox');

    input.addEventListener('input', () => {
      const q = input.value.trim();
      // Limpa lat/lon estaqueado quando o usuário edita
      delete input.dataset.lat;
      delete input.dataset.lon;
      if (q.length < MIN_CHARS) { items = []; close(); return; }
      if (q === lastQuery) return;
      lastQuery = q;
      clearTimeout(timer);
      timer = setTimeout(() => fetchSuggestions(q), DEBOUNCE_MS);
    });

    input.addEventListener('keydown', (e) => {
      if (dropdown.hidden) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIdx = Math.min(items.length - 1, activeIdx + 1);
        render();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIdx = Math.max(0, activeIdx - 1);
        render();
      } else if (e.key === 'Enter' && activeIdx >= 0) {
        e.preventDefault();
        pick(items[activeIdx]);
      } else if (e.key === 'Escape') {
        close();
      }
    });

    dropdown.addEventListener('mousedown', (e) => {
      // mousedown (não click) pra não perder o focus antes do pick
      const li = e.target.closest('[data-i]');
      if (!li) return;
      e.preventDefault();
      pick(items[parseInt(li.dataset.i, 10)]);
    });

    document.addEventListener('click', (e) => {
      if (!wrap.contains(e.target)) close();
    });
  }

  function escapeHTML(s) {
    return String(s || '').replace(/[&<>"']/g,
      c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[c]));
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[data-autocomplete="endereco"]')
            .forEach(attach);
  });
})();
