/* The encrypted alphabet, 30ms cadence and left-to-right reveal come from
   templates/pagehome.html in the owner's original core-theme archive.
   Keep original text in the DOM; animate only an aria-hidden overlay. */
(() => {
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const background = document.getElementById('cd-original-background');
  const typing = document.querySelector('[data-original-typing]');
  const active = new Map();
  let typingTimer;
  const canAnimate = () => !reducedMotion.matches && !document.hidden;
  // The brand's brief, deliberately triggered reveal also works with reduced motion.
  const canScramble = element => !document.hidden && (!reducedMotion.matches || element.hasAttribute('data-scramble-brand'));

  function resetTyping() {
    clearTimeout(typingTimer);
    if (typing) typing.textContent = 'DUNE';
  }
  function startTyping() {
    resetTyping();
    if (!typing || !canAnimate() || document.querySelector('[data-scramble-brand].cd-scramble-running')) return;
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
    document.documentElement.toggleAttribute('data-ticker-paused', document.hidden);
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
  reducedMotion.addEventListener('change', syncMotion);
  document.addEventListener('visibilitychange', syncMotion);
  window.addEventListener('pagehide', () => {
    document.documentElement.setAttribute('data-ticker-paused', '');
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
    if (!canScramble(element) || active.has(element)) return;
    const brand = element.hasAttribute('data-scramble-brand');
    if (brand) resetTyping();
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
    const duration = reducedMotion.matches ? 240 : 900;
    let frame;
    let start;
    let last = -30;
    function stop() {
      cancelAnimationFrame(frame);
      visual.remove();
      element.classList.remove('cd-scramble-running');
      active.delete(element);
      if (brand) startTyping();
    }
    active.set(element, {scope, stop});
    function tick(now) {
      if (start === undefined) start = now;
      const elapsed = now - start;
      if (!canScramble(element) || !element.isConnected || !visual.isConnected || elapsed >= duration) { stop(); return; }
      if (elapsed - last >= 30) {
        visual.textContent = scrambleText(original, elapsed / duration);
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
