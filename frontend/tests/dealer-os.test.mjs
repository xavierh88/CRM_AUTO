import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createDemo, filterCustomers, groupPipeline, STAGES } from '../src/dealer-os/model.mjs';

test('fixtures are detached and explicitly synthetic with pending integrations', () => {
  const a = createDemo(); const b = createDemo();
  a.customers[0].name = 'changed';
  assert.notEqual(a.customers[0].name, b.customers[0].name);
  assert.equal(b.integration, 'PENDING_EXTERNAL');
  assert.ok(b.customers.every(c => c.id.startsWith('demo-') && c.synthetic));
  assert.ok(b.actions.every(a => b.customers.some(c => c.id === a.customer_id)));
});
test('search handles case, whitespace and no matches', () => {
  const { customers } = createDemo();
  assert.equal(filterCustomers(customers, '  AVERY ').length, 1);
  assert.equal(filterCustomers(customers, '').length, customers.length);
  assert.equal(filterCustomers(customers, 'absent').length, 0);
});
test('pipeline preserves unknown stages in review and all canonical stages', () => {
  const groups = groupPipeline([...createDemo().customers, { commercial_stage: 'unknown' }]);
  assert.equal(groups.length, STAGES.length + 1);
  assert.equal(groups.at(-1).customers.length, 1);
  assert.equal(groups.flatMap(g => g.customers).length, 4);
  const python = readFileSync(new URL('../../backend/commercial/pipeline.py', import.meta.url), 'utf8');
  const stages = [...python.split('class PipelineProjection')[0].matchAll(/^    \w+ = '([^']+)'/gm)].map(m => m[1]);
  assert.deepEqual(STAGES, stages);
});
test('shell stays protected and contains no transport or document access', () => {
  const app = readFileSync(new URL('../src/App.js', import.meta.url), 'utf8');
  assert.match(app, /path="\/os\/\*" element=\{<ProtectedRoute><DealerOS \/><\/ProtectedRoute>\}/);
  const shell = readFileSync(new URL('../src/dealer-os/DealerOS.jsx', import.meta.url), 'utf8');
  assert.doesNotMatch(shell, /axios|fetch\(|localStorage|\/uploads|tel:|mailto:/);
  assert.match(shell, /PENDING_EXTERNAL/);
});
