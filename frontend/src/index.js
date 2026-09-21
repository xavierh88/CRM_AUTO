import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
// Select the isolated entry before loading CRM modules or authentication.
const App = React.lazy(() => /^\/demo(?:\/|$)/.test(window.location.pathname)
  ? import('./dealer-os/DemoMode')
  : import('./App'));

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <React.Suspense fallback={<p>Loading…</p>}><App /></React.Suspense>
  </React.StrictMode>,
);
