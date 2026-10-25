const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function fixture(load = async () => []) {
  const factories = {};
  const context = {
    Alpine: { data(name, factory) { factories[name] = factory; }, store() {}, start() {} },
    CTFd: {
      fetch() {}, config: { themeSettings: {} }, _functions: { challenge: {} },
      pages: { challenges: { getChallenges: load }, challenge: { displayChallenge: async () => { throw new Error("unavailable"); } } },
    },
    window: { init: { userId: 2 }, location: { hash: "" } },
    sessionStorage: { getItem() { return null; } }, localStorage: { getItem() { return null; }, setItem() {} },
    AbortController, setTimeout, clearTimeout, console, Intl,
  };
  vm.createContext(context);
  const source = fs.readFileSync(path.resolve(__dirname, "../../CTFd/themes/core-theme/assets/js/challenges.js"), "utf8");
  vm.runInContext(source.replace(/^import .*;\r?\n/gm, ""), context);
  return { board: factories.ChallengeBoard(), context };
}

test("network failure exits loading and a retry recovers", async () => {
  let failing = true;
  const { board } = fixture(async () => {
    if (failing) throw new Error("network unavailable");
    return [{ id: 1, name: "First flag", category: "Web" }];
  });
  await board.init();
  assert.equal(board.loaded, true);
  assert.equal(board.loading, false);
  assert.ok(board.error);
  failing = false;
  await board.loadChallenges();
  assert.equal(board.error, "");
  assert.equal(board.challenges.length, 1);
});

test("expired login or malformed API data preserves existing cards", async () => {
  let response = [{ id: 1, name: "First flag", category: "Web" }];
  const { board } = fixture(async () => response);
  await board.init();
  response = { success: false, message: "sign in" };
  await board.loadChallenges();
  assert.ok(board.error);
  assert.equal(board.challenges[0].id, 1);
});

test("search and progress filters compose without changing the source list", async () => {
  const { board } = fixture(async () => [
    { id: 1, name: "First flag", category: "Web", solved_by_me: true, tags: [{ value: "Cookies" }] },
    { id: 2, name: "Cipher", category: "Crypto", attribution: "Mina" },
  ]);
  await board.init();
  board.search = "cookies";
  assert.equal(board.visibleChallenges().length, 1);
  board.solveFilter = "unsolved";
  assert.equal(board.visibleChallenges().length, 0);
  board.search = "mina";
  assert.equal(board.visibleChallenges()[0].id, 2);
  assert.equal(board.challenges.length, 2);
});

test("opening errors and invalid hashes have visible recovery messages", async () => {
  const { board, context } = fixture();
  await board.loadChallenge(1);
  assert.equal(board.opening, false);
  assert.ok(board.openError);
  context.window.location.hash = "#%invalid";
  await board.init();
  assert.ok(board.openError);
});

test("progress excludes hidden previews and filters do not change completion", async () => {
  const { board } = fixture(async () => [
    { id: 1, solved_by_me: true, tags: [{ value: "Easy" }] },
    { id: 2, solved_by_me: false },
    { id: 3, state: "hidden", preview_solved: true },
  ]);
  await board.init();
  assert.equal(board.solvedCount, 1);
  assert.equal(board.progressPercent, 50);
  board.solveFilter = "solved";
  assert.equal(board.progressChallenges.length, 2);
  assert.equal(board.difficulty(board.challenges[0]), "Easy");
  assert.equal(board.difficulty({ value: 100 }), "");
});

test("team progress uses the private team endpoint and preserves a hidden rank", async () => {
  const { board, context } = fixture();
  Object.assign(context.window.init, { userMode: "teams", teamId: 7, urlRoot: "/ctf" });
  let requested;
  context.CTFd.fetch = async url => {
    requested = url;
    return { ok: true, json: async () => ({ success: true, data: { score: 250, place: null } }) };
  };
  await board.loadProgress();
  assert.equal(requested, "/ctf/api/v1/teams/me");
  assert.equal(board.accountStats.score, 250);
  assert.equal(board.accountStats.place, null);
  context.CTFd.fetch = async () => { throw new Error("offline"); };
  await board.loadProgress();
  assert.equal(board.statsError, true);
  assert.equal(board.accountStats.score, 250);
});

test("a slow account API does not hold the board spinner open", async () => {
  const { board, context } = fixture(async () => [{ id: 1 }]);
  let finish;
  context.CTFd.fetch = () => new Promise(resolve => { finish = resolve; });
  await board.init();
  assert.equal(board.loaded, true);
  assert.equal(board.statsLoading, true);
  finish({ ok: true, json: async () => ({ success: true, data: { score: 0 } }) });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(board.statsLoading, false);
});
