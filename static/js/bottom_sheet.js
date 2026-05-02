/* bottom_sheet.js — Tarefa 4.1
 * Bottom sheet arrastável de verdade no mobile.
 * Estados: peek (84px visível), open (88vh), dragging (sem transição).
 */
(function () {
  const sheet = document.getElementById('sheet') || document.querySelector('.sr-sheet');
  if (!sheet) return;
  const grabber = sheet.querySelector('.sr-sheet-grabber');
  const fab = document.getElementById('fabSheet');

  // Em desktop não dragga
  const mq = window.matchMedia('(max-width: 899px)');

  let startY = 0;
  let startTranslate = 0;
  let dragging = false;

  function getTranslate() {
    const m = getComputedStyle(sheet).transform;
    if (m === 'none') return 0;
    return new DOMMatrix(m).m42;
  }
  function setTranslate(px) {
    sheet.style.transform = `translateY(${px}px)`;
  }
  function open() { sheet.dataset.state = 'open'; sheet.style.transform = ''; }
  function peek() { sheet.dataset.state = 'peek'; sheet.style.transform = ''; }

  function onStart(e) {
    if (!mq.matches) return;
    dragging = true;
    sheet.dataset.state = 'dragging';
    startY = (e.touches ? e.touches[0].clientY : e.clientY);
    startTranslate = getTranslate();
  }
  function onMove(e) {
    if (!dragging) return;
    const y = (e.touches ? e.touches[0].clientY : e.clientY);
    const dy = y - startY;
    const next = Math.max(0, startTranslate + dy);
    setTranslate(next);
    e.preventDefault();
  }
  function onEnd() {
    if (!dragging) return;
    dragging = false;
    const cur = getTranslate();
    const sheetH = sheet.getBoundingClientRect().height;
    sheet.style.transform = '';
    if (cur < sheetH * 0.4) open(); else peek();
  }

  grabber?.addEventListener('mousedown', onStart);
  grabber?.addEventListener('touchstart', onStart, { passive: true });
  document.addEventListener('mousemove', onMove);
  document.addEventListener('touchmove', onMove, { passive: false });
  document.addEventListener('mouseup', onEnd);
  document.addEventListener('touchend', onEnd);

  // FAB abre/fecha
  fab?.addEventListener('click', () => {
    if (sheet.dataset.state === 'open') peek(); else open();
  });

  // Click no header também abre
  sheet.querySelector('.sr-sheet-header')?.addEventListener('click', () => {
    if (mq.matches && sheet.dataset.state === 'peek') open();
  });

  // Em desktop, garantir aberto
  function syncDesktop() {
    if (!mq.matches) { sheet.style.transform = ''; sheet.dataset.state = 'open'; }
    else if (sheet.dataset.state !== 'open') sheet.dataset.state = 'peek';
  }
  syncDesktop();
  mq.addEventListener('change', syncDesktop);
})();
