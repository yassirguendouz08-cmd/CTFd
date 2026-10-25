// CTFd owns rendering, validation and scoring; this module manages instance controls.
(() => {
  window.CyberduneInstanceCleanup?.();
  const challenge = CTFd._internal.challenge;
  challenge.data = undefined;
  challenge.renderer = challenge.render = null;
  challenge.preRender = () => {};
  let panel, busy = false, countdown, polling, closed = false, connectable = false;
  const t = value => window.cyberduneChallengeCopy?.[value] ?? value;
  const node = id => panel?.querySelector('#' + id);
  const show = (id, visible) => { const el = node(id); if (el) el.hidden = !visible; };
  const text = (id, value) => { const el = node(id); if (el) el.textContent = value; };
  const valid = () => !closed && panel?.isConnected;
  const message = (state, value) => {
    if (!valid()) return;
    panel.dataset.state = state;
    const labels = {loading: 'Checking', stopped: 'Not started', starting: 'Starting', ready: 'Ready', expired: 'Expired', failed: 'Needs attention', stopping: 'Stopping', extending: 'Extending'};
    text('cm-instance-state', t(labels[state] || 'Checking'));
    text('cm-instance-message', t(value));
  };
  const setBusy = value => {
    busy = value;
    if (!valid()) return;
    panel.setAttribute('aria-busy', String(value));
    panel.querySelectorAll('button').forEach(button => button.disabled = value);
    if (node('cm-copy-connection')) node('cm-copy-connection').disabled = value || !connectable;
    if (value) show('cm-open-connection', false);
  };
  const api = async (method, id) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), method === 'GET' ? 15000 : 300000);
    const url = CTFd.config.urlRoot + '/api/v1/plugins/ctfd-chall-manager/instance';
    try {
      const response = await CTFd.fetch(method === 'GET' ? url + '?challengeId=' + id : url, {
        method, credentials: 'same-origin', signal: controller.signal,
        headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
        ...(method === 'GET' ? {} : {body: JSON.stringify({challengeId: id})})
      });
      if (method === 'GET' && response.status === 404) return null;
      const result = await response.json();
      if (!response.ok || !result.success) {
        throw new Error(response.status === 429 ? 'An instance operation is already in progress. Check again shortly.' :
          response.status === 403 ? (result.message || 'You cannot perform this action right now.') :
          'Instance service could not complete the request. Check status before trying again.');
      }
      return result.data;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('The request timed out. Check status before trying again.');
      throw error;
    } finally { clearTimeout(timeout); }
  };
  const display = data => {
    if (!valid()) return;
    clearInterval(countdown);
    show('cm-panel-loading', false);
    show('cm-retry', false);
    const deadline = data?.until ? Date.parse(data.until) : null;
    const invalidExpiry = !!data?.until && !Number.isFinite(deadline);
    const expired = deadline !== null && deadline <= Date.now();
    connectable = !!data?.connectionInfo && !expired && !invalidExpiry;
    show('whale-panel-stopped', !data && !challenge.data.shared);
    show('whale-panel-started', !!data);
    show('cm-panel-until', deadline !== null && !invalidExpiry);
    text('whale-challenge-lan-domain', data?.connectionInfo || '');
    text('cm-copy-feedback', '');
    show('cm-connection', connectable);
    show('cm-open-connection', false);
    node('cm-open-connection').removeAttribute('href');
    node('cm-copy-connection').disabled = !connectable || busy;
    if (connectable) {
      try {
        const url = new URL(data.connectionInfo);
        if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) {
          node('cm-open-connection').href = url.href;
          show('cm-open-connection', !busy);
        }
      } catch (_) { /* SSH and other connection instructions remain copyable text. */ }
    }
    const pending = !!data && !expired && !invalidExpiry && !connectable;
    show('cm-retry', expired || pending || invalidExpiry);
    message(invalidExpiry ? 'failed' : expired ? 'expired' : pending ? 'starting' : data ? 'ready' : 'stopped', invalidExpiry ? 'Instance expiry could not be read. Check status again.' : expired ? 'Instance expired. Stop it before launching a new one.' :
      pending ? 'The instance is starting. Check status again shortly.' : data ? 'Instance ready.' : challenge.data.shared ? 'The shared instance is not running. Contact an administrator.' : 'Instance not started.');
    if (deadline !== null && !invalidExpiry) {
      const tick = () => {
        if (!valid()) { clearInterval(countdown); return; }
        const seconds = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
        text('whale-challenge-count-down', Math.floor(seconds / 60) + 'm ' + String(seconds % 60).padStart(2, '0') + 's');
        if (!seconds) {
          clearInterval(countdown);
          message('expired', 'Instance expired. Check status to launch again.');
          show('cm-retry', true);
          connectable = false;
          node('cm-copy-connection').disabled = true;
          show('cm-connection', false);
        }
      };
      tick(); countdown = setInterval(tick, 1000);
    }
  };
  const load = async () => {
    if (!valid()) return;
    try { display(await api('GET', challenge.data.id)); }
    catch (error) {
      if (!valid()) return;
      show('cm-panel-loading', false);
      show('cm-retry', true);
      message('failed', error.message);
    }
  };
  const perform = async method => {
    if (busy || !valid()) return;
    const id = challenge.data.id;
    setBusy(true);
    show('cm-retry', false);
    const labels = {POST: ['starting', 'Starting instance…'], DELETE: ['stopping', 'Stopping instance…'], PATCH: ['extending', 'Extending instance…'], RESTART: ['starting', 'Restarting instance…']};
    message(...labels[method]);
    const operationPanel = panel;
    const poll = async () => {
      if (!valid() || panel !== operationPanel || !busy) return;
      try {
        const data = await api('GET', id);
        if (data?.connectionInfo) { text('whale-challenge-lan-domain', data.connectionInfo); show('whale-panel-started', true); }
      } catch (_) { /* The mutation request supplies the actionable error. */ }
      if (valid() && busy) polling = setTimeout(poll, 5000);
    };
    if (method === 'POST') polling = setTimeout(poll, 5000);
    try {
      if (method === 'RESTART') {
        await api('DELETE', id);
        if (!valid()) return;
        await api('POST', id);
      } else { await api(method, id); }
      if (valid() && panel === operationPanel) await load();
    } catch (error) {
      if (valid() && panel === operationPanel) { message('failed', error.message); show('cm-retry', true); }
    } finally {
      clearTimeout(polling);
      if (panel === operationPanel) {
        setBusy(false);
        if (connectable && node('cm-open-connection')?.href) show('cm-open-connection', true);
      }
    }
  };
  challenge.boot = () => perform('POST');
  challenge.renew = () => perform('PATCH');
  challenge.destroy = () => perform('DELETE');
  challenge.restart = () => perform('RESTART');
  challenge.refreshInstance = load;
  challenge.copyConnection = async () => {
    if (!valid() || !connectable || busy) return;
    try {
      await navigator.clipboard.writeText(node('whale-challenge-lan-domain').textContent);
      text('cm-copy-feedback', t('Connection information copied.'));
    } catch (_) { text('cm-copy-feedback', t('Copy is unavailable. Select and copy the connection information above.')); }
  };
  const cleanup = () => { closed = true; clearInterval(countdown); clearTimeout(polling); };
  window.CyberduneInstanceCleanup = cleanup;
  challenge.postRender = () => requestAnimationFrame(async () => {
    panel = document.getElementById('whale-panel'); closed = false;
    if (!panel) return;
    panel.closest('.modal')?.addEventListener('hidden.bs.modal', cleanup, {once: true});
    setBusy(false);
    await load();
    if (valid() && challenge.data.mana_cost > 0 && !challenge.data.shared) {
      try {
        const response = await CTFd.fetch(CTFd.config.urlRoot + '/api/v1/plugins/ctfd-chall-manager/mana');
        const result = await response.json();
        if (valid() && result.success) {
          text('cm-challenge-mana-remaining', result.data.total - result.data.used);
          panel.querySelectorAll('.cm-panel-mana-cost-div').forEach(el => el.hidden = result.data.total === 0);
        }
      } catch (_) { /* Mutation endpoint checks mana authoritatively. */ }
    }
  });
})();
