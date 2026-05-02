/* compartilhar.js — fallback Web Share API (Tarefa 2.6).
 * O wiring efetivo está em mapa.js → wireResultActions().
 * Este arquivo só registra share nativo se o usuário tiver Web Share.
 */
window.SafeRoute = window.SafeRoute || {};
window.SafeRoute.tryNativeShare = async function (url, title, text) {
  if (navigator.share) {
    try { await navigator.share({ url, title, text }); return true; }
    catch { /* cancelado */ }
  }
  return false;
};
