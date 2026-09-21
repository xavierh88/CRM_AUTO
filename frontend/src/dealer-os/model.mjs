// Mirrors backend.commercial.pipeline.Stage; parity is checked without loading the server.
export const STAGES = Object.freeze(['NEW LEAD', 'CONTACTED', 'ENGAGED', 'PREQUALIFY', 'APPLIED', 'APPROVED', 'CONDITIONAL', 'DECLINED', 'APPOINTMENT', 'SHOW', 'NEGOTIATING', 'PENDING DEAL', 'STOP/HOLD', 'SOLD', 'LOST']);

export function createDemo() {
  return {
    integration: 'PENDING_EXTERNAL',
    customers: [
      { id: 'demo-avery', synthetic: true, name: 'Avery Example', commercial_stage: 'NEW LEAD', interest: 'Compact hybrid', source: 'Synthetic website lead', timeline: ['Demo inquiry received', 'Vehicle preferences recorded'] },
      { id: 'demo-jordan', synthetic: true, name: 'Jordan Sample', commercial_stage: 'APPOINTMENT', interest: 'Family SUV', source: 'Synthetic referral', timeline: ['Demo inquiry received', 'Demo appointment requested'] },
      { id: 'demo-robin', synthetic: true, name: 'Robin Test', commercial_stage: 'PENDING DEAL', interest: 'Electric sedan', source: 'Synthetic showroom visit', timeline: ['Demo visit completed', 'Demo deal awaiting review'] },
    ],
    actions: [
      { id: 'demo-action-1', customer_id: 'demo-avery', title: 'Review new inquiry', priority: 'High' },
      { id: 'demo-action-2', customer_id: 'demo-jordan', title: 'Review appointment preferences', priority: 'Normal' },
      { id: 'demo-action-3', customer_id: 'demo-robin', title: 'Review pending deal', priority: 'Normal' },
    ],
  };
}

export function filterCustomers(customers, query) {
  const normalized = query.trim().toLowerCase();
  return customers.filter(customer => `${customer.name} ${customer.interest}`.toLowerCase().includes(normalized));
}

export function groupPipeline(customers) {
  return [...STAGES, 'Needs review'].map(stage => ({
    stage,
    customers: customers.filter(customer => stage === 'Needs review'
      ? !STAGES.includes(customer.commercial_stage)
      : customer.commercial_stage === stage),
  }));
}
