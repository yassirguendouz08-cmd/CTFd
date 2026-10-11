/* Bounded decorative motion. Never generates telemetry, scores or challenge state. */
(() => {
  'use strict';
  document.addEventListener('DOMContentLoaded', () => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const toggle = document.querySelector('[data-motion-toggle]');
    const typed = document.querySelector('[data-operation-copy]');
    let paused = false;
    try { paused = localStorage.getItem('cyberdune-motion') === 'paused'; } catch (_) { /* Storage may be unavailable. */ }
    let timer = null, offset = 0;
    const phrase = typed?.dataset.operationCopy || '';
    const stop = () => { clearTimeout(timer); timer = null; };
    const type = () => {
      if (!typed || paused || reduced.matches || document.hidden || offset >= phrase.length) return;
      typed.textContent = phrase.slice(0, ++offset);
      timer = setTimeout(type, 55);
    };
    const sync = () => {
      stop();
      document.documentElement.dataset.cdMotion = paused || reduced.matches || document.hidden ? 'paused' : 'running';
      if (toggle) {
        toggle.hidden = reduced.matches;
        toggle.setAttribute('aria-pressed', String(paused));
        toggle.textContent = paused ? toggle.dataset.resume : toggle.dataset.pause;
      }
      if (reduced.matches && typed) { typed.textContent = phrase; offset = phrase.length; }
      else if (!paused && !document.hidden) type();
    };
    if (typed && !paused && !reduced.matches) typed.textContent = '';
    else offset = phrase.length;
    toggle?.addEventListener('click', () => {
      paused = !paused;
      try { localStorage.setItem('cyberdune-motion', paused ? 'paused' : 'running'); } catch (_) { /* Optional preference. */ }
      // A paused terminal keeps the complete, readable label.
      if (paused && typed) { typed.textContent = phrase; offset = phrase.length; }
      sync();
    });
    reduced.addEventListener('change', sync);
    document.addEventListener('visibilitychange', sync);
    window.addEventListener('pagehide', stop);
    sync();

    // Observe only actual score text updates and genuine solved-state changes.
    // Initial hydration is remembered without an animation. No polling or extra API calls.
    const board = document.querySelector('#scoreboard') || document.querySelector('.cd-challenge-grid')?.closest('[x-data="ChallengeBoard"]');
    if (!board) return;
    const known = new WeakMap();
    const capture = () => {
      board.querySelectorAll('[data-real-score], .cd-challenge-card').forEach(node => {
        const value = node.matches('.cd-challenge-card') ? node.classList.contains('challenge-solved') : node.textContent;
        if (known.has(node) && known.get(node) !== value && !paused && !reduced.matches && !document.hidden) {
          node.classList.remove('cd-data-changed');
          // Schedule a finite highlight, with cleanup at the end of the animation.
          requestAnimationFrame(() => node.classList.add('cd-data-changed'));
          node.addEventListener('animationend', () => node.classList.remove('cd-data-changed'), {once: true});
        }
        known.set(node, value);
      });
    };
    capture();
    const observer = new MutationObserver(capture);
    observer.observe(board, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['class']});
    window.addEventListener('pagehide', () => observer.disconnect(), {once: true});
  });
})();
