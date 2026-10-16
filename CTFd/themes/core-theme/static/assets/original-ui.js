/* The encrypted alphabet, 30ms cadence and left-to-right reveal come from
   templates/pagehome.html in the owner's original core-theme archive.
   Keep original text in the DOM; animate only an aria-hidden overlay. */
(() => {
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const background = document.getElementById('cd-original-background');
  const toggle = document.querySelector('[data-motion-toggle]');
  const typing = document.querySelector('[data-original-typing]');
  const active = new Map();
  let paused = false;
  let typingTimer;
  try { paused = localStorage.getItem('cyberdune-effects-paused') === 'true'; } catch (_) { /* Optional preference storage. */ }
  const canAnimate = () => !paused && !reducedMotion.matches && !document.hidden;

  function resetTyping() {
    clearTimeout(typingTimer);
    if (typing) typing.textContent = 'DUNE';
  }
  function startTyping() {
    resetTyping();
    if (!typing || !canAnimate()) return;
    let length = 4;
    let deleting = true;
    const step = () => {
      if (!canAnimate()) { resetTyping(); return; }
      length += deleting ? -1 : 1;
      typing.textContent = 'DUNE'.slice(0, length);
      let delay = deleting ? 100 : 150;
      if (length === 0) { deleting = false; delay = 500; }
      if (length === 4) { deleting = true; delay = 2000; }
      typingTimer = setTimeout(step, delay);
    };
    typingTimer = setTimeout(step, 2000);
  }

  function syncMotion() {
    const stopped = !canAnimate();
    document.documentElement.toggleAttribute('data-effects-paused', stopped);
    if (toggle) {
      toggle.hidden = false;
      toggle.disabled = reducedMotion.matches;
      toggle.setAttribute('aria-pressed', String(paused || reducedMotion.matches));
      toggle.textContent = reducedMotion.matches ? 'Reduced motion enabled' : (paused ? 'Resume effects' : 'Pause effects');
    }
    if (background) {
      if (stopped) background.pause();
      else {
        if (!background.hasAttribute('src')) background.src = background.dataset.src;
        background.muted = true;
        background.play().catch(() => { /* The original poster remains if playback is unavailable. */ });
      }
    }
    if (stopped) for (const animation of [...active.values()]) animation.stop();
    startTyping();
  }
  toggle?.addEventListener('click', () => {
    paused = !paused;
    try { localStorage.setItem('cyberdune-effects-paused', String(paused)); } catch (_) { /* Effects still work without storage. */ }
    syncMotion();
  });
  reducedMotion.addEventListener('change', syncMotion);
  document.addEventListener('visibilitychange', syncMotion);
  window.addEventListener('pagehide', () => {
    background?.pause();
    resetTyping();
    for (const animation of [...active.values()]) animation.stop();
  });
  window.addEventListener('pageshow', syncMotion);

  const encryptedChars = '!@#$%^&*()0123456789ABC]HIJKLMefghijklmnopq]vwxyz';
  function scrambleText(text, revealProgress) {
    const chars = Array.from(text);
    return chars.map((char, i) => {
      if (/\s/.test(char) || i / chars.length <= revealProgress) return char;
      return Math.random() < 0.3 ? encryptedChars[Math.floor(Math.random() * encryptedChars.length)] : char;
    }).join('');
  }
  function findTarget(node) {
    if (!(node instanceof Element)) return null;
    const scope = node.closest('a, button');
    const element = node.closest('[data-scramble], .title_container h1, .cd-page-head h1') || scope?.querySelector('[data-scramble]');
    return element ? {element, scope: scope || element} : null;
  }
  function startScramble({element, scope}) {
    if (!canAnimate() || active.has(element)) return;
    const original = element.innerText.trim();
    if (!original || original.length > 160) return;
    element.setAttribute('data-scramble', '');
    const visual = document.createElement('span');
    visual.className = 'cd-scramble-visual';
    visual.setAttribute('aria-hidden', 'true');
    visual.style.color = getComputedStyle(element).color;
    visual.textContent = scrambleText(original, 0);
    element.appendChild(visual);
    element.classList.add('cd-scramble-running');
    let frame;
    let start;
    let last = -30;
    function stop() {
      cancelAnimationFrame(frame);
      visual.remove();
      element.classList.remove('cd-scramble-running');
      active.delete(element);
    }
    active.set(element, {scope, stop});
    function tick(now) {
      if (start === undefined) start = now;
      const elapsed = now - start;
      if (!canAnimate() || !element.isConnected || !visual.isConnected || elapsed >= 900) { stop(); return; }
      if (elapsed - last >= 30) {
        visual.textContent = scrambleText(original, elapsed / 900);
        last = elapsed;
      }
      frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
  }
  document.addEventListener('pointerover', event => {
    if (event.pointerType === 'touch') return;
    const target = findTarget(event.target);
    if (target && !target.scope.contains(event.relatedTarget)) startScramble(target);
  });
  document.addEventListener('focusin', event => {
    const target = findTarget(event.target);
    if (target) startScramble(target);
  });
  function stopDeparted(event) {
    for (const animation of [...active.values()]) {
      if (animation.scope.contains(event.target) && !animation.scope.contains(event.relatedTarget)) animation.stop();
    }
  }
  document.addEventListener('pointerout', stopDeparted);
  document.addEventListener('focusout', stopDeparted);

  // Restore the original Explore menu with keyboard and outside-click dismissal.
  const explore = document.querySelector('.cd-explore');
  const exploreButton = document.getElementById('exploreDropdownToggle');
  const exploreMenu = document.getElementById('exploreDropdown');
  function closeExplore() {
    if (exploreMenu) exploreMenu.hidden = true;
    exploreButton?.setAttribute('aria-expanded', 'false');
  }
  exploreButton?.addEventListener('click', () => {
    const opening = exploreMenu.hidden;
    exploreMenu.hidden = !opening;
    exploreButton.setAttribute('aria-expanded', String(opening));
    if (opening) {
      const accountMenu = document.getElementById('accountDropdown');
      if (accountMenu) accountMenu.hidden = true;
      document.getElementById('accountDropdownToggle')?.setAttribute('aria-expanded', 'false');
    }
  });
  exploreButton?.addEventListener('keydown', event => {
    if (event.key !== 'ArrowDown') return;
    event.preventDefault();
    exploreMenu.hidden = false;
    exploreButton.setAttribute('aria-expanded', 'true');
    exploreMenu.querySelector('a')?.focus();
  });
  document.addEventListener('click', event => { if (!explore?.contains(event.target)) closeExplore(); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && exploreMenu && !exploreMenu.hidden) {
      event.stopImmediatePropagation();
      closeExplore();
      exploreButton.focus();
    }
  }, true);
  matchMedia('(min-width: 1200px)').addEventListener('change', closeExplore);
  explore?.addEventListener('focusout', event => { if (!explore.contains(event.relatedTarget)) closeExplore(); });
  exploreMenu?.querySelectorAll('a').forEach(link => {
    if (new URL(link.href, location.href).pathname === location.pathname) {
      link.setAttribute('aria-current', 'page');
      exploreButton.classList.add('is-current');
    }
  });
  syncMotion();
})();
