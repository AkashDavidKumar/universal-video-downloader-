import { useState, useRef, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import './styles.css';

/* =============================================
   Toast Notification Hook
   ============================================= */

function useToast() {
  const [toast, setToast] = useState(null);
  const timerRef = useRef(null);
  const show = (msg, type = 'success') => {
    clearTimeout(timerRef.current);
    setToast({ msg, type });
    timerRef.current = setTimeout(() => setToast(null), 3500);
  };
  return [toast, show];
}

function copyToClipboard(text, show) {
  navigator.clipboard.writeText(text).then(() => show('Copied to clipboard!', 'success'));
}

/* =============================================
   Demo Data Fallback
   ============================================= */

const DEMO_VIDEOS = [
  {
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    title: 'Rick Astley — Never Gonna Give You Up (Official Music Video)',
    uploader: 'Rick Astley',
    duration: 213.0,
    thumbnail: 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=300',
    description: 'The official video for Never Gonna Give You Up by Rick Astley.',
    formats: [
      { format_id: 'yt_137', resolution: '1080p', ext: 'mp4', filesize: 33230000 },
      { format_id: 'yt_136', resolution: '720p', ext: 'mp4', filesize: 12260000 },
      { format_id: 'yt_18',  resolution: '360p', ext: 'mp4', filesize: 6910000 },
      { format_id: 'yt_140', resolution: 'audio', ext: 'm4a', filesize: 1510000 },
    ],
  },
  {
    url: 'https://vimeo.com/76979871',
    title: 'The Mountain — Time Lapse by Terje Sorgjerd',
    uploader: 'Terje Sorgjerd',
    duration: 282.0,
    thumbnail: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=300',
    description: 'Time lapse shot on El Teide, Spain.',
    formats: [
      { format_id: 'vm_1080', resolution: '1080p', ext: 'mp4', filesize: 50540000 },
      { format_id: 'vm_720',  resolution: '720p', ext: 'mp4', filesize: 23070000 },
      { format_id: 'vm_360',  resolution: '360p', ext: 'mp4', filesize: 8490000 },
    ],
  },
];

/* =============================================
   App Component
   ============================================= */

function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [selectedFmt, setFmt] = useState('');
  const [downloads, setDownloads] = useState([]);
  const [isDemoMode, setIsDemoMode] = useState(true);
  const [toast, showToast] = useToast();
  const inputRef = useRef(null);

  // Auto-detect if API backend is available
  useEffect(() => {
    async function checkBackend() {
      try {
        const res = await fetch('/api/settings');
        if (res.ok) {
          setIsDemoMode(false);
          showToast('Connected to Python backend!', 'success');
        }
      } catch (err) {
        setIsDemoMode(true);
      }
    }
    checkBackend();
  }, []);

  // Poll for downloads list
  useEffect(() => {
    let intervalId;
    async function fetchDownloads() {
      if (isDemoMode) return;
      try {
        const res = await fetch('/api/downloads');
        if (res.ok) {
          const data = await res.json();
          setDownloads(data);
        }
      } catch (err) {
        console.error('Error fetching downloads:', err);
      }
    }

    fetchDownloads();
    intervalId = setInterval(fetchDownloads, 1000);
    return () => clearInterval(intervalId);
  }, [isDemoMode]);

  async function handleAnalyze() {
    if (!url.trim()) {
      showToast('Please enter a URL first.', 'error');
      return;
    }
    setLoading(true);
    setResult(null);

    if (isDemoMode) {
      // Simulated delay
      await new Promise(r => setTimeout(r, 1200));
      const found = DEMO_VIDEOS.find(v => url.trim().startsWith(v.url.slice(0, 30)));
      if (found) {
        setResult(found);
        setFmt(found.formats[0].format_id);
        showToast('Analysis complete (Demo)!', 'success');
      } else {
        showToast(
          'Simulated check: Please paste Rick Astley\'s link or Vimeo 76979871 to trigger demo metadata.',
          'error'
        );
      }
      setLoading(false);
      return;
    }

    // Real API Call
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
        if (data.formats && data.formats.length > 0) {
          setFmt(data.formats[0].format_id);
        }
        showToast('Media page analyzed successfully!', 'success');
      } else {
        const err = await res.json();
        showToast(`Analysis failed: ${err.detail || 'Unknown error'}`, 'error');
      }
    } catch (err) {
      showToast('Backend connection lost.', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function handleDownload() {
    if (!result || !selectedFmt) return;

    if (isDemoMode) {
      showToast('Simulating download queue...', 'success');
      // Create local demo task
      const demoId = Date.now();
      const formatObj = result.formats.find(f => f.format_id === selectedFmt);
      const totalSize = formatObj?.filesize || 1024 * 1024 * 20;

      const newDemoTask = {
        id: demoId,
        title: result.title,
        status: 'downloading',
        progress: 0,
        downloaded_bytes: 0,
        total_bytes: totalSize,
        speed: 0,
        eta: 0,
        resolution: formatObj?.resolution || 'unknown',
        container: formatObj?.ext || 'mp4',
      };

      setDownloads(prev => [newDemoTask, ...prev]);

      // Progress Simulation
      let pct = 0;
      const interval = setInterval(() => {
        pct = Math.min(pct + Math.floor(Math.random() * 10) + 5, 100);
        const speedBytes = Math.floor(Math.random() * 1024 * 1024 * 3) + 1024 * 512; // 0.5 - 3.5 MB/s
        setDownloads(prev =>
          prev.map(t => {
            if (t.id === demoId) {
              const status = pct >= 100 ? 'completed' : 'downloading';
              return {
                ...t,
                progress: pct,
                status,
                downloaded_bytes: Math.floor((pct / 100) * totalSize),
                speed: status === 'completed' ? 0 : speedBytes,
                eta: status === 'completed' ? 0 : Math.ceil(((100 - pct) / 100) * (totalSize / speedBytes)),
              };
            }
            return t;
          })
        );
        if (pct >= 100) {
          clearInterval(interval);
        }
      }, 400);
      return;
    }

    // Real API Call
    try {
      const res = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: result.url, format_id: selectedFmt }),
      });
      if (res.ok) {
        showToast('Download queued successfully!', 'success');
      } else {
        const err = await res.json();
        showToast(`Failed to download: ${err.detail || 'Unknown error'}`, 'error');
      }
    } catch (err) {
      showToast('Could not reach backend server.', 'error');
    }
  }

  async function handleAction(downloadId, action) {
    if (isDemoMode) {
      setDownloads(prev =>
        prev.map(t => {
          if (t.id === downloadId) {
            if (action === 'pause') return { ...t, status: 'paused', speed: 0 };
            if (action === 'resume') return { ...t, status: 'downloading' };
            if (action === 'cancel') return { ...t, status: 'cancelled', speed: 0 };
          }
          return t;
        })
      );
      showToast(`Download ${action}d (Simulated)`, 'success');
      return;
    }

    try {
      const res = await fetch(`/api/downloads/${downloadId}/${action}`, { method: 'POST' });
      if (res.ok) {
        showToast(`Download ${action}d successfully.`, 'success');
      } else {
        showToast(`Failed to ${action} download.`, 'error');
      }
    } catch (err) {
      showToast('Error communicating with backend.', 'error');
    }
  }

  function handlePaste() {
    navigator.clipboard.readText().then(t => setUrl(t)).catch(() => {});
  }

  const handleTryDemo = () => {
    setUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
    document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' });
    if (inputRef.current) inputRef.current.focus();
  };

  // Helper format sizing
  const formatBytes = bytes => {
    if (!bytes || bytes <= 0) return 'unknown size';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const formatSpeed = speed => {
    if (!speed || speed <= 0) return '0 KB/s';
    const mb = speed / (1024 * 1024);
    return mb >= 0.1 ? `${mb.toFixed(2)} MB/s` : `${(speed / 1024).toFixed(1)} KB/s`;
  };

  return (
    <>
      {/* Navbar */}
      <nav className="navbar">
        <div className="container navbar-inner">
          <a href="#" className="nav-logo">
            <span className="nav-logo-icon">⬇</span>
            <span>VidDown Pro</span>
          </a>
          <ul className="nav-links">
            <li><a href="#demo" className="nav-link">Downloader</a></li>
            <li><a href="#features" className="nav-link">Features</a></li>
            <li><a href="#install" className="nav-link">Setup</a></li>
            <li>
              <span className={`nav-badge ${isDemoMode ? 'demo-badge' : 'connected-badge'}`}>
                {isDemoMode ? 'Demo Mode' : 'Connected'}
              </span>
            </li>
          </ul>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero section container">
        <div className="hero-eyebrow">
          <span>⚡</span> FastAPI + React Full-Stack App
        </div>
        <h1 className="hero-title">High Speed Downloader<br />Right in Your Browser.</h1>
        <p className="hero-subtitle">
          Enjoy the high-fidelity web client that routes download requests directly to Python's concurrent engine, providing fully transparent speed indicators, ETA estimations, and stream resolution selections.
        </p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={handleTryDemo}>
            ▶ Open Downloader
          </button>
          <a href="#install" className="btn btn-secondary">
            📚 Quick Start Guide
          </a>
        </div>
      </section>

      {/* Main Downloader Workspace */}
      <section id="demo" className="demo-section">
        <div className="container">
          <div className="section-heading">
            <h2>Media Control Hub</h2>
            <p>Paste your link to fetch video codecs, resolutions, and initiate direct network streaming.</p>
          </div>

          <div className="demo-card" style={{ maxWidth: '850px' }}>
            <div style={{ display: 'flex', gap: '0.6rem', marginBottom: '1.5rem' }}>
              <input
                ref={inputRef}
                className="demo-input"
                type="url"
                placeholder="Paste video page URL here (e.g., https://youtube.com/watch?v=...)"
                value={url}
                onChange={e => setUrl(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleAnalyze()}
              />
              <button className="btn btn-secondary btn-sm" onClick={handlePaste}>📋 Paste</button>
              <button
                className={`btn btn-primary btn-sm btn-analyze ${loading ? 'loading' : ''}`}
                onClick={handleAnalyze}
                disabled={loading}
              >
                {loading ? <span className="btn-spinner" /> : '🔍'}
                {loading ? 'Analyzing…' : 'Analyze'}
              </button>
            </div>

            {/* Analysis Meta Output */}
            {result && (
              <div className="demo-result" style={{ marginBottom: '1.5rem' }}>
                <div className="result-meta">
                  <div className="result-thumb">
                    {result.thumbnail ? (
                      <img src={result.thumbnail} alt={result.title} />
                    ) : (
                      '🎬'
                    )}
                  </div>
                  <div className="result-info">
                    <div className="result-title" title={result.title}>{result.title}</div>
                    <div className="result-uploader">👤 {result.uploader || 'Unknown'}</div>
                    <div className="result-duration">⏱ {result.duration ? `${Math.floor(result.duration / 60)}m ${Math.floor(result.duration % 60)}s` : 'Unknown'}</div>
                  </div>
                </div>

                <div className="format-row">
                  <select
                    className="format-select"
                    value={selectedFmt}
                    onChange={e => setFmt(e.target.value)}
                  >
                    {result.formats?.map(f => (
                      <option key={f.format_id} value={f.format_id}>
                        {f.resolution} ({f.ext}) — {formatBytes(f.filesize)}
                      </option>
                    ))}
                  </select>
                  <button className="btn btn-primary btn-sm" onClick={handleDownload}>
                    ⬇ Download
                  </button>
                </div>
              </div>
            )}

            {/* Downloads Progress List */}
            {downloads.length > 0 && (
              <div style={{ marginTop: '2rem' }}>
                <div className="demo-label" style={{ marginBottom: '1rem' }}>Active Download Manager</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  {downloads.map(task => (
                    <div
                      key={task.id}
                      style={{
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-md)',
                        padding: '1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.6rem',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div
                          style={{
                            fontWeight: '600',
                            fontSize: '0.9rem',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            maxWidth: '65%',
                          }}
                          title={task.title}
                        >
                          {task.title}
                        </div>
                        <div
                          style={{
                            fontSize: '0.78rem',
                            padding: '0.2rem 0.6rem',
                            borderRadius: '999px',
                            background:
                              task.status === 'completed'
                                ? 'rgba(34,197,94,0.15)'
                                : task.status === 'failed'
                                ? 'rgba(239,68,68,0.15)'
                                : 'rgba(56,189,248,0.15)',
                            color:
                              task.status === 'completed'
                                ? 'var(--green)'
                                : task.status === 'failed'
                                ? 'var(--red)'
                                : 'var(--accent)',
                          }}
                        >
                          {task.status.toUpperCase()}
                        </div>
                      </div>

                      {/* Info and controls */}
                      <div className="progress-bar-bg">
                        <div
                          className="progress-bar-fill"
                          style={{ width: `${task.progress || 0}%` }}
                        />
                      </div>

                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          fontSize: '0.78rem',
                          color: 'var(--text-muted)',
                        }}
                      >
                        <div>
                          {formatBytes(task.downloaded_bytes)} / {formatBytes(task.total_bytes)}
                          {task.status === 'downloading' && (
                            <>
                              {' · '}
                              <span style={{ color: 'var(--accent)' }}>{formatSpeed(task.speed)}</span>
                              {' · '}
                              <span>ETA: {task.eta ? `${task.eta}s` : '--'}</span>
                            </>
                          )}
                        </div>

                        {/* Controls */}
                        {task.status !== 'completed' && task.status !== 'failed' && task.status !== 'cancelled' && (
                          <div style={{ display: 'flex', gap: '0.4rem' }}>
                            {task.status === 'downloading' ? (
                              <button
                                className="btn btn-ghost btn-sm"
                                style={{ padding: '0.15rem 0.5rem', borderRadius: '4px' }}
                                onClick={() => handleAction(task.id, 'pause')}
                              >
                                ⏸ Pause
                              </button>
                            ) : (
                              <button
                                className="btn btn-ghost btn-sm"
                                style={{ padding: '0.15rem 0.5rem', borderRadius: '4px' }}
                                onClick={() => handleAction(task.id, 'resume')}
                              >
                                ▶ Resume
                              </button>
                            )}
                            <button
                              className="btn btn-ghost btn-sm"
                              style={{
                                padding: '0.15rem 0.5rem',
                                borderRadius: '4px',
                                borderColor: 'rgba(239,68,68,0.3)',
                                color: 'var(--red)',
                              }}
                              onClick={() => handleAction(task.id, 'cancel')}
                            >
                              🛑 Cancel
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Installation and run instructions */}
      <section id="install" className="section container">
        <div className="section-heading">
          <h2>Run the Server Locally</h2>
          <p>Launch the Python FastAPI server in one command and load the dashboard.</p>
        </div>
        <div className="code-block" style={{ position: 'relative' }}>
          <button
            className="copy-btn"
            onClick={() => copyToClipboard('python main.py web', showToast)}
          >
            Copy
          </button>
          <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
            <span className="cm"># 1. Start the backend server & serve the UI bundle</span>{"\n"}
            python main.py web{"\n\n"}
            <span className="cm"># 2. Access the video control interface in your browser</span>{"\n"}
            Open: http://127.0.0.1:8000
          </pre>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          <div className="footer-links">
            <a href="https://github.com/AkashDavidKumar/universal-video-downloader-" target="_blank" rel="noreferrer">GitHub Repo</a>
            <a href="https://github.com/AkashDavidKumar/universal-video-downloader-/blob/main/README.md" target="_blank" rel="noreferrer">README</a>
            <a href="https://github.com/AkashDavidKumar/universal-video-downloader-/blob/main/deploy_guide.md" target="_blank" rel="noreferrer">Deploy Guide</a>
          </div>
          <p>© {new Date().getFullYear()} Universal Video Downloader — Full-Stack Web Interface</p>
        </div>
      </footer>

      {/* Toasts rendering */}
      {toast && <div className={`toast toast-${toast.type}`}>{toast.msg}</div>}
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
