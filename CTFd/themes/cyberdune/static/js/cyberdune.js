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
  const categoryIcon = category => {
    const value = String(category || '').toLowerCase();
    if (/web/.test(value)) return 'fas fa-globe';
    if (/crypt/.test(value)) return 'fas fa-key';
    if (/pwn|binary/.test(value)) return 'fas fa-microchip';
    if (/rev/.test(value)) return 'fas fa-code';
    if (/forensic/.test(value)) return 'fas fa-fingerprint';
    if (/osint/.test(value)) return 'fas fa-search';
    return 'fas fa-flag';
  };
  window.Cyberdune = { matches, categoryIcon };

  document.addEventListener('DOMContentLoaded', () => {
    const root = window.init || {};
    const home = document.querySelector('[data-home-workspace]');
    if (home) {
      const get = async route => {
        try {
          const response = await fetch(`${root.urlRoot || ''}/api/v1/${route}`, {credentials: 'same-origin'});
          if (!response.ok) return null;
          const payload = await response.json();
          return payload.success && Array.isArray(payload.data) ? payload.data : null;
        } catch (_) { return null; }
      };
      if (home.dataset.loadChallenges === 'true') get('challenges').then(challenges => {
        if (!challenges) return;
        const visible = challenges.filter(challenge => !challenge.state || challenge.state === 'visible');
        const categories = [...new Set(visible.map(challenge => challenge.category))];
        home.querySelector('[data-visible-count]')?.replaceChildren(String(visible.length));
        home.querySelector('[data-category-count]')?.replaceChildren(String(categories.length));
        const grid = home.querySelector('[data-home-categories]');
        categories.forEach(category => {
          const link = document.createElement('a'); link.className = 'cd-home-category';
          link.href = `${root.urlRoot || ''}/challenges?category=${encodeURIComponent(category)}`;
          const title = document.createElement('strong'); title.textContent = category;
          const icon = document.createElement('i'); icon.className = `cd-category-symbol ${categoryIcon(category)}`; icon.setAttribute('aria-hidden', 'true'); title.prepend(icon);
          const detail = document.createElement('span');
          detail.textContent = `${visible.filter(challenge => challenge.category === category).length} · ${copy('Available challenges')} ↗`;
          link.append(title, detail); grid.append(link);
        });
        home.querySelector('[data-categories-empty]').hidden = categories.length > 0;
      });
      if (home.dataset.loadScores === 'true') get('scoreboard').then(standings => {
        if (!standings) return;
        home.querySelector('[data-standing-count]').textContent = standings.length;
        const leaders = home.querySelector('[data-home-leaders]');
        standings.slice(0, 3).forEach((standing, index) => {
          const row = document.createElement('li');
          const rank = document.createElement('span'); rank.textContent = String(index + 1).padStart(2, '0');
          const link = document.createElement('a'); link.textContent = standing.name;
          const destination = new URL(standing.account_url, location.origin);
          link.href = destination.origin === location.origin ? destination.href : `${root.urlRoot || ''}/scoreboard`;
          const points = document.createElement('strong'); points.textContent = standing.score;
          row.append(rank, link, points); leaders.append(row);
        });
        home.querySelector('[data-leaders-empty]').hidden = standings.length > 0;
      });
    }
    const statusNodes = document.querySelectorAll('[data-event-status]');
    const stamp = value => value && Number.isFinite(Number(value)) ? Number(value) * 1000 : null;
    const event = root.cyberdunePresentation || {};
    const start = event.mode === 'event' ? stamp(event.start) : null;
    const end = event.mode === 'event' ? stamp(event.end) : null;
    const dateFormat = new Intl.DateTimeFormat(undefined, {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short'});
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
      document.querySelectorAll('[data-event-primary]').forEach(link => {
        link.href = scheduled ? '#cd-platform-panel-title' : ended ? link.dataset.scoreboardUrl : link.dataset.challengesUrl;
        link.querySelector('[data-event-primary-label]').textContent = scheduled ? copy('View event details') : ended ? copy('View standings') : copy('Take the challenge');
      });
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
    if (event.mode === 'event' && start && end && end > start && statusNodes.length) { tick(); setInterval(() => { if (!document.hidden) tick(); }, 1000); }

    // Link highlighting respects reverse-proxy prefixes and admin-created pages.
    const highlightNavigation = () => {
      const path = location.pathname.replace(/\/$/, '');
      document.querySelectorAll('.cd-nav a.nav-link').forEach(link => {
        const target = new URL(link.href, location.href);
        const active = target.pathname.replace(/\/$/, '') === path && target.hash === location.hash;
        link.classList.toggle('active', active);
        if (active) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      });
    };
    highlightNavigation();
    window.addEventListener('hashchange', highlightNavigation);

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
