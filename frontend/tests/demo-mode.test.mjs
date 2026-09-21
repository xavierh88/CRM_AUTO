import test from 'node:test';
import assert from 'node:assert/strict';
import { createDemoSession, demoCustomer, advanceTour, restartTour, resetDemo } from '../src/dealer-os/demo-session.mjs';

test('demo lookup uses exact fixture membership and never accepts arbitrary client IDs', () => {
  const session = createDemoSession();
  for (const id of ['fictional-real-client', 'demo-unknown', '../clients', null]) {
    assert.equal(demoCustomer(session, id), undefined);
  }
  assert.equal(demoCustomer(session, 'demo-avery').synthetic, true);
  assert.equal(session.identity.role, 'DEMO');
  assert.equal(session.identity.token, undefined);
});
test('reset discards all changes and tour restart preserves data', () => {
  const session = createDemoSession();
  session.data.customers[0].name = 'Edited Example';
  session.tour = 2;
  assert.equal(restartTour(session).tour, 0);
  assert.equal(restartTour(session).data.customers[0].name, 'Edited Example');
  const reset = resetDemo();
  assert.equal(reset.data.customers[0].name, 'Avery Example');
  assert.equal(reset.tour, 0);
  assert.notEqual(reset.data, session.data);
});
test('tour has bounded ES/EN steps and completion', () => {
  for (const language of ['en', 'es']) {
    let session = createDemoSession(language);
    assert.equal(session.steps.length, 3);
    for (let i = 0; i < 5; i++) session = advanceTour(session);
    assert.equal(session.tour, session.steps.length);
    assert.equal(restartTour(session).tour, 0);
  }
  assert.equal(createDemoSession('unknown').language, 'en');
});
test('cross-feature fixtures reference only fictional demo customers', () => {
  const { data } = createDemoSession();
  for (const feature of ['leads', 'appointments', 'vehicles', 'messages', 'sales', 'finances', 'prequalifications']) {
    assert.ok(data[feature].length);
    for (const row of data[feature]) {
      assert.equal(row.synthetic, true);
      assert.ok(row.id.startsWith('demo-'));
      if (row.customer_id) assert.ok(data.customers.some(c => c.id === row.customer_id));
    }
  }
  assert.equal(data.messages[0].status, 'MOCK');
  assert.equal(data.prequalifications[0].status, 'PENDING_EXTERNAL');
});

test('demo entry does not mount CRM authentication or import transports', async () => {
  const { readFileSync } = await import('node:fs');
  const entry = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');
  assert.match(entry, /React.lazy/);
  assert.match(entry, /\? import\('\.\/dealer-os\/DemoMode'\)/);
  assert.match(entry, /: import\('\.\/App'\)/);
  assert.doesNotMatch(entry, /import App from/);
  for (const file of ['DemoMode.jsx', 'demo-session.mjs', 'model.mjs']) {
    const source = readFileSync(new URL(`../src/dealer-os/${file}`, import.meta.url), 'utf8');
    assert.doesNotMatch(source, /axios|fetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon|localStorage|sessionStorage|AuthProvider|\/api\/|\/uploads|mailto:|tel:|\/dashboard/);
  }
});

test('every demo record is explicitly synthetic and reset isolates all feature arrays', () => {
  const session = createDemoSession('es');
  const untouched = createDemoSession('es');
  for (const [feature, rows] of Object.entries(session.data)) {
    if (!Array.isArray(rows)) continue;
    for (const row of rows) assert.equal(row.synthetic, true, `${feature}: ${row.id}`);
    rows[0].description = 'Synthetic local edit';
    rows.push({ id: 'demo-local-edit', synthetic: true });
  }
  session.steps[0] = 'Edited tour';
  assert.deepEqual(resetDemo('es'), untouched);
  assert.equal(untouched.language, 'es');
});
