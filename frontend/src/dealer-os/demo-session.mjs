import { createDemo } from './model.mjs';

const tours = {
  en: ['Review fictional leads and next actions.', 'Explore customers, appointments and vehicles.', 'Review simulated sales and finance. External actions are disabled.'],
  es: ['Revisa prospectos ficticios y próximas acciones.', 'Explora clientes, citas y vehículos.', 'Revisa ventas y finanzas simuladas. Las acciones externas están deshabilitadas.'],
};

export function createDemoSession(language = 'en') {
  language = Object.hasOwn(tours, language) ? language : 'en';
  const data = createDemo();
  const fixture = (id, fields) => ({ id: `demo-${id}`, synthetic: true, ...fields });
  Object.assign(data, {
    actions: data.actions.map(action => ({ ...action, synthetic: true, status: 'MOCK' })),
    leads: [fixture('lead-1', { customer_id: 'demo-avery', status: 'NEW LEAD' })],
    appointments: [fixture('appointment-1', { customer_id: 'demo-jordan', description: 'Fictional showroom visit', status: 'MOCK' })],
    vehicles: [fixture('vehicle-1', { description: 'Example Motors · Fictional electric sedan', status: 'MOCK' })],
    messages: [fixture('message-1', { customer_id: 'demo-avery', description: 'Simulated SMS: Welcome to the fictional showroom.', status: 'MOCK' })],
    sales: [fixture('sale-1', { customer_id: 'demo-robin', amount: 24000, currency: 'USD', status: 'MOCK' })],
    finances: [fixture('finance-1', { customer_id: 'demo-robin', amount: 18000, currency: 'USD', status: 'MOCK' })],
    prequalifications: [fixture('prequal-1', { customer_id: 'demo-robin', status: 'PENDING_EXTERNAL' })],
  });
  return { identity: { id: 'demo-visitor', role: 'DEMO', is_demo: true }, data,
    language, steps: [...tours[language]], tour: 0 };
}

// Exact membership, never a prefix-based permission or an API fallback.
export function demoCustomer(session, id) {
  return session.data.customers.find(customer => customer.id === id);
}
export function advanceTour(session) {
  return { ...session, tour: Math.min(session.tour + 1, session.steps.length) };
}
export function restartTour(session) {
  return { ...session, tour: 0 };
}
export function resetDemo(language = 'en') {
  return createDemoSession(language);
}
