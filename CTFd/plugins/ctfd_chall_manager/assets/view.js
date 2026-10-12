// CTFd owns rendering, validation and scoring; this module manages instance controls.
(() => {
  window.CyberduneInstanceCleanup?.();
  const challenge = CTFd._internal.challenge;
  challenge.data = undefined;
  challenge.renderer = challenge.render = null;
  challenge.preRender = () => {};
  let panel, busy = false, countdown, polling, closed = false;
  const node = id => panel?.querySelector('#' + id);
  const show = (id, visible) => { const el = node(id); if (el) el.hidden = !visible; };
  const text = (id, value) => { const el = node(id); if (el) el.textContent = value; };
  const valid = () => !closed && panel?.isConnected;
  const message = (state, value) => {
    if (!valid()) return;
    panel.dataset.state = state;
    text('cm-instance-message', value);
  };
  const setBusy = value => {
    busy = value;
    if (!valid()) return;
    panel.setAttribute('aria-busy', String(value));
    panel.querySelectorAll('button').forEach(button => button.disabled = value);
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
    const expired = data?.until && Date.parse(data.until) <= Date.now();
    show('whale-panel-stopped', !data && !challenge.data.shared);
    show('whale-panel-started', !!data);
    show('cm-panel-until', !!data?.until);
    text('whale-challenge-lan-domain', data?.connectionInfo || '');
    message(expired ? 'expired' : data ? 'ready' : 'stopped', expired ? 'Instance expired. Stop it before launching a new one.' :
      data ? 'Instance ready.' : challenge.data.shared ? 'The shared instance is not running. Contact an administrator.' : 'Instance not started.');
    if (data?.until) {
      const tick = () => {
        if (!valid()) { clearInterval(countdown); return; }
        const seconds = Math.max(0, Math.ceil((Date.parse(data.until) - Date.now()) / 1000));
        text('whale-challenge-count-down', Math.floor(seconds / 60) + 'm ' + String(seconds % 60).padStart(2, '0') + 's');
        if (!seconds) {
          clearInterval(countdown);
          message('expired', 'Instance expired. Check status to launch again.');
          show('cm-retry', true);
          node('cm-copy-connection').disabled = true;
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
      if (panel === operationPanel) setBusy(false);
    }
  };
  challenge.boot = () => perform('POST');
  challenge.renew = () => perform('PATCH');
  challenge.destroy = () => perform('DELETE');
  challenge.restart = () => perform('RESTART');
  challenge.refreshInstance = load;
  challenge.copyConnection = async () => {
    try {
      await navigator.clipboard.writeText(node('whale-challenge-lan-domain').textContent);
      message('ready', 'Connection information copied.');
    } catch (_) { message('ready', 'Copy is unavailable. Select and copy the connection information above.'); }
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
