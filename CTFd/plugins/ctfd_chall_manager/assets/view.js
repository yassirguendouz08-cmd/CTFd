// CTFd owns rendering and flag submission; these controls only manage instances.
(() => {
  const challenge = CTFd._internal.challenge;
  challenge.data = undefined;
  challenge.renderer = null;
  challenge.render = null;
  challenge.preRender = () => {};
  let timer;
  let busy = false;
  let currentPanel;
  const node = id => document.getElementById(id);
  const show = (id, visible) => { const el = node(id); if (el) el.style.display = visible ? "" : "none"; };
  const text = (id, value) => { const el = node(id); if (el) el.textContent = value; };
  const setBusy = value => {
    busy = value;
    document.querySelectorAll("#whale-panel button").forEach(el => { el.disabled = value; });
  };
  const valid = panel => panel && panel.isConnected && panel === node("whale-panel");
  const api = async (method, id) => {
    const url = CTFd.config.urlRoot + "/api/v1/plugins/ctfd-chall-manager/instance";
    const response = await CTFd.fetch(method === "GET" ? url + "?challengeId=" + id : url, {
      method, credentials: "same-origin",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      ...(method === "GET" ? {} : { body: JSON.stringify({ challengeId: id }) })
    });
    if (method === "GET" && response.status === 404) return null;
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.message || "Instance service unavailable. Contact an administrator.");
    return result.data;
  };
  const display = (data, panel, id) => {
    if (!valid(panel)) return;
    clearInterval(timer);
    show("cm-panel-loading", false);
    show("whale-panel-stopped", !data && !challenge.data.shared);
    show("whale-panel-started", !!data);
    show("cm-panel-until", !!(data && data.until));
    text("whale-challenge-lan-domain", data ? data.connectionInfo || "Preparing connection…" : "");
    if (!data && challenge.data.shared) text("cm-instance-message", "The shared instance has not been started by an administrator.");
    if (data && data.until) {
      const tick = () => {
        if (!valid(panel)) { clearInterval(timer); return; }
        const seconds = Math.max(0, Math.ceil((new Date(data.until) - Date.now()) / 1000));
        text("whale-challenge-count-down", seconds ? Math.floor(seconds / 60) + "m " + String(seconds % 60).padStart(2, "0") + "s" : "Expiring…");
        if (!seconds) { clearInterval(timer); }
      };
      tick();
      timer = setInterval(tick, 1000);
    }
  };
  const load = async (id, panel) => {
    try {
      const data = await api("GET", id);
      display(data, panel, id);
      if (!data && challenge.data.mana_cost > 0 && valid(panel)) {
        const response = await CTFd.fetch(CTFd.config.urlRoot + "/api/v1/plugins/ctfd-chall-manager/mana");
        const result = await response.json();
        if (valid(panel) && result.success) {
          text("cm-challenge-mana-remaining", result.data.total - result.data.used);
          panel.querySelectorAll(".cm-panel-mana-cost-div").forEach(el => { el.hidden = result.data.total === 0; });
        }
      }
    } catch (error) {
      if (!valid(panel)) return;
      show("cm-panel-loading", false);
      show("whale-panel-stopped", false);
      show("whale-panel-started", false);
      text("cm-instance-message", error.message);
    }
  };
  const perform = async method => {
    if (busy) return;
    const panel = node("whale-panel");
    const id = challenge.data.id;
    setBusy(true);
    text("cm-instance-message", "Working…");
    try {
      if (method === "RESTART") {
        await api("DELETE", id);
        if (!valid(panel)) return;
        await api("POST", id);
      } else {
        await api(method, id);
      }
      if (!valid(panel)) return;
      text("cm-instance-message", method === "DELETE" ? "Instance destroyed." : "Instance updated.");
      await load(id, panel);
    } catch (error) {
      if (valid(panel)) text("cm-instance-message", error.message);
    } finally {
      if (valid(panel)) setBusy(false);
    }
  };
  challenge.boot = () => perform("POST");
  challenge.renew = () => perform("PATCH");
  challenge.destroy = () => perform("DELETE");
  challenge.restart = () => perform("RESTART");
  challenge.postRender = () => {
    clearInterval(timer);
    // Alpine inserts the modal view after CTFd's rendering callback.
    requestAnimationFrame(() => {
      currentPanel = node("whale-panel");
      setBusy(false);
      if (currentPanel) load(challenge.data.id, currentPanel);
    });
  };
})();
