/* dark_mode.js — toggle persistente em localStorage. */
(function () {
  const KEY = 'saferoute:theme';
  const btn = document.getElementById('themeToggle');

  function apply(t) {
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem(KEY, t);
  }
  function current() {
    return document.documentElement.getAttribute('data-theme') || 'claro';
  }
  btn?.addEventListener('click', () => {
    apply(current() === 'escuro' ? 'claro' : 'escuro');
  });
})();
