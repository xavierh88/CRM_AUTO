import { useState } from 'react';
import { Link, NavLink, Route, Routes, useParams } from 'react-router-dom';
import { CheckSquare, Users, BarChart3 } from 'lucide-react';
import { createDemo, filterCustomers, groupPipeline } from './model.mjs';
import './dealer-os.css';

function CustomerLink({ customer }) {
  return <Link className="os-card os-customer" to={`/os/customers/${customer.id}`}>
    <strong>{customer.name}</strong><span>{customer.interest}</span>
    <small>{customer.commercial_stage || 'Needs review'}</small>
  </Link>;
}

function ActionCenter({ data }) {
  return <><h1>Action Center</h1><p>Review the next steps for your demo workspace.</p>
    <div className="os-grid">{data.actions.map(action => <article className="os-card" key={action.id}>
      <small>{action.priority} priority · MOCK</small><h2>{action.title}</h2>
      <p>{data.customers.find(customer => customer.id === action.customer_id)?.name}</p>
      <Link className="os-button" to={`/os/customers/${action.customer_id}`}>Review customer</Link>
    </article>)}</div></>;
}

function Customers({ data }) {
  const [query, setQuery] = useState('');
  const customers = filterCustomers(data.customers, query);
  return <><h1>Customers</h1><label htmlFor="os-search">Search demo customers or vehicle interests</label>
    <input id="os-search" type="search" value={query} onChange={event => setQuery(event.target.value)} />
    <p role="status">{customers.length} customers</p>
    <div className="os-grid">{customers.map(customer => <CustomerLink key={customer.id} customer={customer} />)}</div>
    {customers.length === 0 && <p>No matching customers. Try another name or vehicle interest.</p>}</>;
}

function Customer360({ data }) {
  const { customerId } = useParams();
  const customer = data.customers.find(item => item.id === customerId);
  if (!customer) return <><h1>Customer not found</h1><Link to="/os/customers">Back to customers</Link></>;
  return <><Link to="/os/customers">← Customers</Link><h1>{customer.name}</h1><p>Customer 360 · Fictional profile</p>
    <div className="os-grid"><section className="os-card"><h2>Overview</h2><dl>
      <dt>Commercial stage</dt><dd>{customer.commercial_stage}</dd>
      <dt>Vehicle interest</dt><dd>{customer.interest}</dd>
      <dt>Source</dt><dd>{customer.source}</dd></dl></section>
      <section className="os-card"><h2>Activity</h2><ol>{customer.timeline.map(item => <li key={item}>{item}</li>)}</ol></section>
      <section className="os-card"><h2>Communications & documents</h2>
        <p>PENDING_EXTERNAL — messaging, credit and document access are unavailable in this preview.</p>
      </section></div></>;
}

function Pipeline({ data }) {
  const [stage, setStage] = useState('All');
  const groups = groupPipeline(data.customers);
  const visible = groups.filter(group => stage === 'All' ? group.customers.length > 0 : group.stage === stage);
  return <><h1>Commercial pipeline</h1><p>Read-only demo stages. No deal or credit changes are submitted.</p>
    <label htmlFor="os-stage">Stage</label><select id="os-stage" value={stage} onChange={event => setStage(event.target.value)}>
      <option>All</option>{groups.map(group => <option key={group.stage}>{group.stage}</option>)}</select>
    <div className="os-grid">{visible.map(group => <section key={group.stage} aria-label={group.stage}>
      <h2>{group.stage} <small>({group.customers.length})</small></h2>
      {group.customers.map(customer => <CustomerLink key={customer.id} customer={customer} />)}
      {!group.customers.length && <p>No customers in this stage.</p>}
    </section>)}</div></>;
}

export default function DealerOS() {
  const [data] = useState(createDemo);
  return <div className="dealer-os"><a className="os-skip" href="#os-content">Skip to content</a>
    <header className="os-header"><Link to="/os">Dealer AI OS</Link><span>MOCK · Synthetic data only</span><Link to="/dashboard">CRM</Link></header>
    <main id="os-content" tabIndex={-1}><Routes>
      <Route index element={<ActionCenter data={data} />} />
      <Route path="customers" element={<Customers data={data} />} />
      <Route path="customers/:customerId" element={<Customer360 data={data} />} />
      <Route path="pipeline" element={<Pipeline data={data} />} />
      <Route path="*" element={<><h1>Page not found</h1><Link to="/os">Action Center</Link></>} />
    </Routes></main>
    <nav className="os-nav" aria-label="Dealer OS navigation">
      <NavLink to="/os" end><CheckSquare aria-hidden="true" />Actions</NavLink>
      <NavLink to="/os/customers"><Users aria-hidden="true" />Customers</NavLink>
      <NavLink to="/os/pipeline"><BarChart3 aria-hidden="true" />Pipeline</NavLink>
    </nav></div>;
}
