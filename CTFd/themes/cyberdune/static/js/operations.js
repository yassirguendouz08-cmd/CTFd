/* Finite feedback for real score and solved-state updates. No decorative runtime. */
(() => {
  'use strict';
  document.addEventListener('DOMContentLoaded', () => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    // Observe only actual score text updates and genuine solved-state changes.
    // Initial hydration is remembered without an animation. No polling or extra API calls.
    const board = document.querySelector('#scoreboard') || document.querySelector('.cd-challenge-grid')?.closest('[x-data="ChallengeBoard"]');
    if (!board) return;
    const known = new WeakMap();
    const capture = () => {
      board.querySelectorAll('[data-real-score], .cd-challenge-card').forEach(node => {
        const value = node.matches('.cd-challenge-card') ? node.classList.contains('challenge-solved') : node.textContent;
        if (known.has(node) && known.get(node) !== value && !reduced.matches && !document.hidden) {
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
