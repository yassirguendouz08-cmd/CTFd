/* CYBERDUNE enhancements. CTFd owns authentication, scoring and submissions. */
(() => {
  'use strict';
  const copy = key => window.cyberduneCopy?.[key] || key;
  const matches = (challenge, query, category, state) => {
    const text = `${challenge.name} ${challenge.category} ${(challenge.tags || []).map(t => t.value).join(' ')}`.toLowerCase();
    return (!query || text.includes(query.trim().toLowerCase())) &&
      (!category || challenge.category === category) &&
      (state === 'all' || (state === 'solved' ? challenge.solved_by_me : !challenge.solved_by_me));
  };
  window.Cyberdune = { matches };

  document.addEventListener('DOMContentLoaded', () => {
    // Decorative effects never issue network requests or execute displayed commands.
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    const motionButtons = [...document.querySelectorAll('[data-motion-toggle]')];
    const terminal = document.querySelector('[data-terminal]');
    const staticTerminal = terminal ? terminal.innerHTML : '';
    let userPaused = false, timer, step = 0, letter = 0, commandText;
    try { userPaused = localStorage.getItem('cyberdune-effects-paused') === 'true'; } catch (_) { /* Storage is optional. */ }
    const steps = [
      {command: 'cat mission.txt', output: copy('Find the weakness. Follow the clues. Capture the flag.')},
      {command: './begin --mindset curious', output: copy('Curiosity loaded. Your next solve starts here.')},
      {command: 'printf "stay curious\\n"', output: copy('stay curious')}
    ];
    const paused = () => userPaused || reducedMotion.matches;
    const schedule = delay => { clearTimeout(timer); if (!paused() && !document.hidden && terminal) timer = setTimeout(type, delay); };
    function type() {
      if (paused() || document.hidden || !terminal) return;
      if (!commandText) {
        if (step === 0) terminal.replaceChildren();
        const row = document.createElement('div'); row.className = 'cd-terminal-line';
        const prompt = document.createElement('span'); prompt.className = 'cd-prompt'; prompt.textContent = 'challenger@cyberdune:~$ ';
        commandText = document.createElement('span'); commandText.className = 'cd-terminal-typing';
        row.append(prompt, commandText); terminal.append(row); letter = 0;
      }
      const current = steps[step];
      if (letter < current.command.length) { commandText.textContent += current.command[letter++]; schedule(65); return; }
      commandText.classList.remove('cd-terminal-typing');
      const output = document.createElement('div'); output.className = 'cd-terminal-output'; output.textContent = current.output;
      terminal.append(output); commandText = null; step = (step + 1) % steps.length;
      schedule(step === 0 ? 5500 : 1200);
    }
    function updateMotion() {
      clearTimeout(timer);
      document.body.classList.toggle('cd-effects-paused', paused());
      motionButtons.forEach(button => {
        button.textContent = reducedMotion.matches ? copy('Reduced motion') : userPaused ? copy('Resume effects') : copy('Pause effects');
        button.setAttribute('aria-pressed', String(paused()));
        button.disabled = reducedMotion.matches;
      });
      if (reducedMotion.matches && terminal) { terminal.innerHTML = staticTerminal; commandText = null; step = 0; }
      schedule(700);
    }
    motionButtons.forEach(button => button.addEventListener('click', () => {
      userPaused = !userPaused;
      try { localStorage.setItem('cyberdune-effects-paused', String(userPaused)); } catch (_) { /* Continue without persistence. */ }
      updateMotion();
    }));
    reducedMotion.addEventListener('change', updateMotion);
    document.addEventListener('visibilitychange', () => { if (document.hidden) clearTimeout(timer); else schedule(700); });
    updateMotion();
    const root = window.init || {};
    const statusNodes = document.querySelectorAll('[data-event-status]');
    const stamp = value => value && Number.isFinite(Number(value)) ? Number(value) * 1000 : null;
    const start = stamp(root.start), end = stamp(root.end);
    const dateFormat = new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'});
    for (const [selector, value] of [['[data-event-start]', start], ['[data-event-end]', end]]) {
      document.querySelectorAll(selector).forEach(node => {
        if (value) { node.textContent = dateFormat.format(value); node.dateTime = new Date(value).toISOString(); }
      });
    }
    const tick = () => {
      const now = Date.now();
      const scheduled = start && now < start;
      const ended = end && now >= end;
      const label = scheduled ? copy('Starts soon') : ended ? copy('Event ended') : start ? copy('Event live') : end ? copy('Event open') : copy('Schedule not set');
      statusNodes.forEach(node => { node.textContent = label; node.dataset.state = scheduled ? 'scheduled' : ended ? 'ended' : start || end ? 'live' : 'unset'; });
      const target = scheduled ? start : !ended ? end : null;
      document.querySelectorAll('[data-countdown]').forEach(node => {
        node.hidden = !target;
        if (!target) return;
        const seconds = Math.max(0, Math.floor((target - now) / 1000));
        const days = Math.floor(seconds / 86400);
        const hh = String(Math.floor(seconds / 3600) % 24).padStart(2, '0');
        const mm = String(Math.floor(seconds / 60) % 60).padStart(2, '0');
        const ss = String(seconds % 60).padStart(2, '0');
        node.querySelector('[data-countdown-label]').textContent = scheduled ? copy('STARTS IN') : copy('ENDS IN');
        node.querySelector('[data-countdown-value]').textContent = `${days ? days + 'd ' : ''}${hh}:${mm}:${ss}`;
      });
    };
    if (statusNodes.length) { tick(); setInterval(() => { if (!document.hidden) tick(); }, 1000); }

    // Link highlighting respects reverse-proxy prefixes and admin-created pages.
    const path = location.pathname.replace(/\/$/, '');
    document.querySelectorAll('.cd-nav a.nav-link').forEach(link => {
      if (new URL(link.href, location.href).pathname.replace(/\/$/, '') === path) {
        link.classList.add('active'); link.setAttribute('aria-current', 'page');
      }
    });

    // Keep CTFd's original labels, form fields, validation and CSRF token.
    let passwordIndex = 0;
    document.querySelectorAll('.cd-auth input[type=password]').forEach(input => {
      if (!input.id) input.id = `cd-password-${++passwordIndex}`;
      const wrap = document.createElement('div'); wrap.className = 'cd-password';
      input.parentNode.insertBefore(wrap, input); wrap.append(input);
      const button = document.createElement('button'); button.type = 'button'; button.textContent = copy('Show');
      button.setAttribute('aria-controls', input.id); button.setAttribute('aria-label', copy('Show password')); button.setAttribute('aria-pressed', 'false');
      button.addEventListener('click', () => {
        const visible = input.type === 'password'; input.type = visible ? 'text' : 'password';
        button.textContent = visible ? copy('Hide') : copy('Show'); button.setAttribute('aria-label', visible ? copy('Hide password') : copy('Show password')); button.setAttribute('aria-pressed', String(visible));
      });
      wrap.append(button);
    });

    // Tables remain semantic; overflow stays within their own scroll container.
    const wrapTables = scope => scope.querySelectorAll('table.table').forEach(table => {
      if (table.parentElement.classList.contains('cd-table-scroll') || table.parentElement.classList.contains('table-responsive')) return;
      const wrap = document.createElement('div'); wrap.className = 'cd-table-scroll'; wrap.tabIndex = 0;
      wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', 'Scrollable data table');
      table.parentNode.insertBefore(wrap, table); wrap.append(table);
    });
    wrapTables(document);
    const modal = document.getElementById('challenge-window');
    if (modal) {
      modal.addEventListener('shown.bs.modal', () => {
        wrapTables(modal);
        const feedback = modal.querySelector('.notification-row');
        if (feedback) { feedback.setAttribute('aria-live', 'polite'); feedback.setAttribute('aria-atomic', 'true'); }
        const input = modal.querySelector('#challenge-input');
        if (input) { input.setAttribute('aria-label', 'Flag submission'); input.autocomplete = 'off'; input.spellcheck = false; input.focus(); }
      });
    }
  });
})();
