const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

async function fixture(initial) {
  let data = initial, clock = Date.now(), tick, rendered, copied;
  const nodes = new Map();
  for (const id of ['cm-instance-message', 'cm-instance-state', 'cm-panel-loading', 'cm-retry', 'whale-panel-stopped', 'whale-panel-started', 'cm-panel-until', 'whale-challenge-lan-domain', 'cm-copy-feedback', 'cm-connection', 'cm-copy-connection', 'cm-open-connection', 'whale-challenge-count-down']) {
    nodes.set(id, { hidden: false, disabled: false, textContent: '', removeAttribute(name) { delete this[name]; } });
  }
  const panel = {
    isConnected: true, dataset: {},
    querySelector: selector => nodes.get(selector.slice(1)),
    querySelectorAll: selector => selector === 'button' ? [nodes.get('cm-copy-connection')] : [],
    setAttribute() {}, closest: () => ({ addEventListener() {} }),
  };
  class Clock extends Date { static now() { return clock; } }
  const challenge = {};
  const context = {
    window: {}, document: { getElementById: () => panel },
    CTFd: { _internal: { challenge }, config: { urlRoot: '' }, fetch: async () => ({ status: data ? 200 : 404, ok: true, json: async () => ({ success: true, data }) }) },
    requestAnimationFrame: callback => { rendered = callback(); },
    navigator: { clipboard: { writeText: async value => { copied = value; } } },
    AbortController, URL, Date: Clock, setTimeout, clearTimeout,
    setInterval: callback => { tick = callback; return 1; }, clearInterval() {},
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.resolve(__dirname, '../../CTFd/plugins/ctfd_chall_manager/assets/view.js'), 'utf8'), context);
  challenge.data = { id: 5, shared: false, mana_cost: 0 };
  challenge.postRender();
  await rendered;
  return { nodes, panel, challenge, context, get copied() { return copied; }, setData(value) { data = value; }, advance(ms) { clock += ms; tick(); } };
}

test('ready HTTP instance exposes a safe URL and copying preserves its status', async () => {
  const f = await fixture({ connectionInfo: 'https://worker.example.test:32001/', until: new Date(Date.now() + 60000).toISOString() });
  assert.equal(f.panel.dataset.state, 'ready');
  assert.equal(f.nodes.get('cm-open-connection').hidden, false);
  assert.equal(f.nodes.get('cm-open-connection').href, 'https://worker.example.test:32001/');
  await f.challenge.copyConnection();
  assert.equal(f.copied, 'https://worker.example.test:32001/');
  assert.equal(f.panel.dataset.state, 'ready');
  assert.ok(f.nodes.get('cm-copy-feedback').textContent.includes('copied'));
});

test('expiration hides the endpoint and blocks copying even after an operation finishes', async () => {
  const f = await fixture({ connectionInfo: 'http://worker.example.test/', until: new Date(Date.now() + 60000).toISOString() });
  f.advance(61000);
  assert.equal(f.panel.dataset.state, 'expired');
  assert.equal(f.nodes.get('cm-connection').hidden, true);
  await f.challenge.copyConnection();
  assert.equal(f.copied, undefined);
  f.context.CTFd.fetch = async () => { throw new Error('unavailable'); };
  await f.challenge.destroy();
  assert.equal(f.nodes.get('cm-copy-connection').disabled, true);
  assert.equal(f.nodes.get('cm-open-connection').hidden, true);
});

test('starting, invalid expiry and non-web instructions never expose an unsafe link', async () => {
  const f = await fixture({});
  assert.equal(f.panel.dataset.state, 'starting');
  assert.equal(f.nodes.get('cm-retry').hidden, false);
  f.setData({ connectionInfo: 'https://worker.example.test/' });
  await f.challenge.refreshInstance();
  assert.equal(f.nodes.get('cm-open-connection').hidden, false);
  for (const connectionInfo of ['ssh -L 8080:127.0.0.1:32001 worker', 'javascript:alert(1)', 'https://name:password@worker.example.test/']) {
    f.setData({ connectionInfo });
    await f.challenge.refreshInstance();
    assert.equal(f.nodes.get('cm-open-connection').hidden, true);
    assert.equal(f.nodes.get('cm-open-connection').href, undefined);
  }
  f.setData({ connectionInfo: 'https://worker.example.test/', until: 'invalid' });
  await f.challenge.refreshInstance();
  assert.equal(f.panel.dataset.state, 'failed');
  assert.equal(f.nodes.get('cm-copy-connection').disabled, true);
});
