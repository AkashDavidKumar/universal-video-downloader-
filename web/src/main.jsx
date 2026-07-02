import React from 'react';
import ReactDOM from 'react-dom/client';
import './styles.css';

function App() {
  return (
    <main className="shell">
      <section className="card">
        <span className="eyebrow">React UI • Minimal animation</span>
        <h1>Universal Video Downloader</h1>
        <p>
          This lightweight React experience provides a polished, deployable landing experience for the downloader project while keeping the Python backend intact.
        </p>
        <div className="actions">
          <button>Launch Downloader</button>
          <button className="secondary">View Deploy Guide</button>
        </div>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
