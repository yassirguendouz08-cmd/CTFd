// Regression: Alpine evaluates profile category rows before solves have loaded.
// Run with: node tests/frontend/profile-breakdown.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
for (const file of ['users/private.js', 'users/public.js', 'teams/private.js', 'teams/public.js']) {
  const factories = {};
  const Alpine = {data: (name, factory) => { factories[name] = factory; }, store() {}, start() {}};
  const source = fs.readFileSync(path.join(__dirname, '../../CTFd/themes/core-theme/assets/js', file), 'utf8')
    .replace(/^import .*?;\r?\n/gm, '');
  vm.runInNewContext(source, {Alpine, CTFd: {}, window: {}, colorHash: category => category});
  const profile = factories[file.startsWith('users') ? 'UserGraphs' : 'TeamGraphs']();
  assert.equal(profile.getCategoryBreakdown().length, 0, `${file}: pending request`);
  assert.equal(profile.getSolvePercentage(), '0.00');
  assert.equal(profile.getFailPercentage(), '0.00');
  profile.solveCount = 3;
  profile.failCount = 1;
  assert.equal(profile.getSolvePercentage(), '75.00');
  assert.equal(profile.getFailPercentage(), '25.00');
  profile.solves = {data: []};
  assert.equal(profile.getCategoryBreakdown().length, 0, `${file}: empty account`);
  profile.solves.data = ['Web', 'Web', 'Crypto'].map(category => ({challenge: {category}}));
  const rows = profile.getCategoryBreakdown();
  assert.equal(rows.length, 2);
  assert.equal(rows.find(row => row.name === 'Web').count, 2);
  assert.equal(rows.find(row => row.name === 'Crypto').count, 1);
  if ('percent' in rows[0]) assert.equal(Number(rows.find(row => row.name === 'Web').percent).toFixed(2), '66.67');
  console.log(`PASS: ${file} pending, empty and loaded category breakdowns`);
}
