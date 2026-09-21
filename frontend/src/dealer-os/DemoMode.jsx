import { useState } from 'react';
import { createDemoSession, demoCustomer, advanceTour, restartTour, resetDemo } from './demo-session.mjs';
import { filterCustomers, groupPipeline } from './model.mjs';
import './dealer-os.css';

const features = ['leads', 'appointments', 'vehicles', 'messages', 'sales', 'finances', 'prequalifications'];

export default function DemoMode() {
  const [session, setSession] = useState(createDemoSession);
  const [view, setView] = useState('customers');
  const [query, setQuery] = useState('');
  const [customerId, setCustomerId] = useState(null);
  const customer = demoCustomer(session, customerId);
  const reset = () => {
    setSession(resetDemo(session.language));
    setView('customers'); setQuery(''); setCustomerId(null);
  };
  return <div className="dealer-os">
    <a className="os-skip" href="#demo-content">Skip to content</a>
    <header className="os-header"><strong>DEMO · Dealer AI OS</strong><span>100% fictional data · MOCK</span></header>
    <main id="demo-content" tabIndex={-1}>
      <h1>Demo workspace</h1>
      <p>No real messages, documents or credit actions. Integrations: PENDING_EXTERNAL.</p>
      <button className="os-button" onClick={reset}>Reset demo data</button>{' '}
      <button className="os-button" onClick={() => setSession(restartTour)}>Restart tour</button>{' '}
      <label>Tour language <select value={session.language} onChange={event => {
        const fresh = createDemoSession(event.target.value);
        setSession(previous => ({ ...previous, language: fresh.language, steps: fresh.steps, tour: 0 }));
      }}><option value="en">English</option><option value="es">Español</option></select></label>
      <section aria-label="Guided tour" aria-live="polite" lang={session.language}>
        {session.tour < session.steps.length ? <>
          <p>{session.tour + 1} / {session.steps.length}: {session.steps[session.tour]}</p>
          <button className="os-button" onClick={() => setSession(advanceTour)}>{session.language === 'es' ? 'Siguiente' : 'Next'}</button>
        </> : <p>{session.language === 'es' ? 'Tour completado' : 'Tour complete'}</p>}
      </section>
      <nav aria-label="Demo features">{['customers', 'actions', 'pipeline', ...features].map(feature =>
        <button className="os-button" key={feature} aria-pressed={view === feature} onClick={() => { setView(feature); setCustomerId(null); }}>{feature}</button>)}</nav>
      <h2>{view}</h2>
      {view === 'customers' && <><label htmlFor="demo-search">Search fictional customers</label>
        <input id="demo-search" value={query} onChange={event => setQuery(event.target.value)} />
        {filterCustomers(session.data.customers, query).map(item => <button className="os-card" key={item.id} onClick={() => setCustomerId(item.id)}>{item.name} · {item.interest}</button>)}
        {!filterCustomers(session.data.customers, query).length && <p>No matching customers.</p>}</>}
      {view === 'pipeline' && groupPipeline(session.data.customers).filter(group => group.customers.length).map(group =>
        <section className="os-card" key={group.stage}><h3>{group.stage}</h3>{group.customers.map(item => <p key={item.id}>{item.name}</p>)}</section>)}
      {['actions', ...features].includes(view) && session.data[view].map(item => <article className="os-card" key={item.id}>
        <h3>{item.title || item.description || item.id}</h3><p>{item.status || 'MOCK'}</p>
        {item.amount !== undefined && <p>{item.amount} {item.currency} · Fictional amount</p>}
        {item.customer_id && <button className="os-button" onClick={() => setCustomerId(item.customer_id)}>Review {demoCustomer(session, item.customer_id)?.name}</button>}
      </article>)}
      {customer && <section className="os-card" aria-label="Fictional customer profile"><h2>{customer.name}</h2><p>{customer.interest} · {customer.commercial_stage}</p>
        <ul>{customer.timeline.map(entry => <li key={entry}>{entry}</li>)}</ul>
        <button className="os-button" onClick={() => setCustomerId(null)}>Close profile</button></section>}
    </main>
  </div>;
}
