import { useState, useRef, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import './styles.css';

/* =============================================
   Tiny utility hooks & helpers
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
   Mock demo: simulates analyze + download
   ============================================= */

const DEMO_VIDEOS = [
  {
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    title: 'Rick Astley — Never Gonna Give You Up (Official Music Video)',
    uploader: 'Rick Astley',
    duration: '3m 33s',
    thumb: '🎵',
    formats: [
      { id: 'yt_137', label: '1072×1920 (mp4) — 31.7 MB' },
      { id: 'yt_136', label: '714×1280 (mp4) — 11.7 MB' },
      { id: 'yt_18',  label: '358×640 (mp4)  — 6.6 MB'  },
      { id: 'yt_140', label: 'Audio only (m4a) — 1.4 MB' },
    ],
  },
  {
    url: 'https://vimeo.com/76979871',
    title: 'The Mountain — Time Lapse by Terje Sorgjerd',
    uploader: 'Terje Sorgjerd',
    duration: '4m 42s',
    thumb: '🏔',
    formats: [
      { id: 'vm_1080', label: '1920×1080 (mp4) — 48.2 MB' },
      { id: 'vm_720',  label: '1280×720  (mp4) — 22.0 MB' },
      { id: 'vm_360',  label: '640×360   (mp4) — 8.1 MB'  },
    ],
  },
];

function matchDemo(url) {
  return DEMO_VIDEOS.find(v => url.trim().startsWith(v.url.slice(0, 30)));
}

/* =============================================
   Navbar
   ============================================= */

function Navbar() {
  return (
    <nav className="navbar">
      <div className="container navbar-inner">
        <a href="#" className="nav-logo">
          <span className="nav-logo-icon">⬇</span>
          <span>VidDown</span>
        </a>
        <ul className="nav-links">
          <li><a href="#demo"     className="nav-link">Demo</a></li>
          <li><a href="#features" className="nav-link">Features</a></li>
          <li><a href="#install"  className="nav-link">Install</a></li>
          <li>
            <a
              href="https://github.com/AkashDavidKumar/universal-video-downloader-"
              className="nav-link"
              target="_blank" rel="noreferrer"
            >
              GitHub <span className="nav-badge">Open Source</span>
            </a>
          </li>
        </ul>
      </div>
    </nav>
  );
}

/* =============================================
   Hero
   ============================================= */

function Hero({ onTryDemo }) {
  return (
    <section className="hero section container">
      <div className="hero-eyebrow">
        <span>⚡</span> Powered by yt-dlp + Python
      </div>
      <h1 className="hero-title">Download Any Video,<br />From Anywhere.</h1>
      <p className="hero-subtitle">
        A powerful open-source video downloader with a desktop GUI, a full CLI,
        and a plugin-based extractor engine. Supports YouTube, Vimeo, and hundreds of sites.
      </p>
      <div className="hero-actions">
        <button className="btn btn-primary" onClick={onTryDemo}>
          ▶ Try the Demo
        </button>
        <a
          href="https://github.com/AkashDavidKumar/universal-video-downloader-"
          className="btn btn-secondary"
          target="_blank" rel="noreferrer"
        >
          ⭐ Star on GitHub
        </a>
        <a href="#install" className="btn btn-ghost">
          ⬇ Install Guide
        </a>
      </div>
      <div className="hero-stats">
        {[
          { value: '1 000+', label: 'Supported Sites' },
          { value: 'yt-dlp', label: 'Backend Engine'  },
          { value: 'MIT',    label: 'Open Source'      },
        ].map(s => (
          <div key={s.label} className="hero-stat">
            <div className="hero-stat-value">{s.value}</div>
            <div className="hero-stat-label">{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* =============================================
   Downloader Demo Panel
   ============================================= */

function DownloaderDemo({ autoFocus }) {
  const [url, setUrl]           = useState('');
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [selectedFmt, setFmt]   = useState('');
  const [progress, setProgress] = useState(null); // null | { pct, speed }
  const [toast, showToast]      = useToast();
  const inputRef = useRef(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) inputRef.current.focus();
  }, [autoFocus]);

  async function handleAnalyze() {
    if (!url.trim()) { showToast('Please enter a URL first.', 'error'); return; }
    setLoading(true);
    setResult(null);
    setProgress(null);

    // Simulate network delay
    await new Promise(r => setTimeout(r, 1400 + Math.random() * 600));

    const found = matchDemo(url);
    if (found) {
      setResult(found);
      setFmt(found.formats[0].id);
      showToast('Analysis complete!', 'success');
    } else {
      showToast(
        'Note: This is a demo — paste a YouTube or Vimeo URL for a simulated result. ' +
        'Run the real app locally to download anything.',
        'error',
      );
    }
    setLoading(false);
  }

  async function handleDownload() {
    if (!result || !selectedFmt) return;
    setProgress({ pct: 0, speed: '0 KB/s' });

    // Simulate download progress
    let pct = 0;
    const tick = setInterval(() => {
      pct = Math.min(pct + Math.floor(Math.random() * 12 + 4), 100);
      const speed = (Math.random() * 2 + 0.5).toFixed(2) + ' MB/s';
      setProgress({ pct, speed });
      if (pct >= 100) {
        clearInterval(tick);
        showToast('✅ Download simulated! Run the app locally to actually save files.', 'success');
        setTimeout(() => setProgress(null), 2000);
      }
    }, 200);
  }

  function handlePaste() {
    navigator.clipboard.readText().then(t => setUrl(t)).catch(() => {});
  }

  const fmt = result?.formats.find(f => f.id === selectedFmt);

  return (
    <section id="demo" className="demo-section">
      <div className="container">
        <div className="section-heading">
          <h2>Live Demo</h2>
          <p>Paste a YouTube or Vimeo URL below to see the extractor in action.</p>
        </div>

        <div className="demo-card">
          <div className="demo-label">Video URL</div>
          <div className="demo-url-row">
            <input
              ref={inputRef}
              className="demo-input"
              type="url"
              placeholder="https://www.youtube.com/watch?v=..."
              value={url}
              onChange={e => setUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAnalyze()}
            />
            <button className="btn btn-secondary btn-sm" onClick={handlePaste}>📋 Paste</button>
            <button
              className={`btn btn-primary btn-sm btn-analyze${loading ? ' loading' : ''}`}
              onClick={handleAnalyze}
              disabled={loading}
            >
              {loading ? <span className="btn-spinner" /> : '🔍'}
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>

          {/* Result area */}
          <div className={`demo-result${result ? '' : ' hidden'}`}>
            {result && (
              <>
                <div className="result-meta">
                  <div className="result-thumb">{result.thumb}</div>
                  <div className="result-info">
                    <div className="result-title">{result.title}</div>
                    <div className="result-uploader">👤 {result.uploader}</div>
                    <div className="result-duration">⏱ {result.duration}</div>
                  </div>
                </div>

                <hr className="divider" />

                <div className="format-row">
                  <select
                    className="format-select"
                    value={selectedFmt}
                    onChange={e => setFmt(e.target.value)}
                  >
                    {result.formats.map(f => (
                      <option key={f.id} value={f.id}>{f.label}</option>
                    ))}
                  </select>
                  <button className="btn btn-primary btn-sm" onClick={handleDownload}>
                    ⬇ Download
                  </button>
                </div>

                {progress && (
                  <div className={`progress-wrap${progress !== null ? ' visible' : ''}`}>
                    <div className="progress-label">
                      <span>{fmt?.label}</span>
                      <span>{progress.pct}% · {progress.speed}</span>
                    </div>
                    <div className="progress-bar-bg">
                      <div className="progress-bar-fill" style={{ width: `${progress.pct}%` }} />
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`toast toast-${toast.type}`}>{toast.msg}</div>
      )}
    </section>
  );
}

/* =============================================
   Features
   ============================================= */

const FEATURES = [
  { icon: '🔌', title: 'Plugin Extractor System',    desc: 'Drop-in extractor plugins for any site. Ships with YouTube (yt-dlp), Vimeo, and a generic HTTP fallback.' },
  { icon: '🖥',  title: 'Desktop GUI (PySide6)',      desc: 'Native cross-platform desktop app with dark/light themes, progress cards, and format selection.' },
  { icon: '⌨',  title: 'Full CLI Interface',          desc: 'Analyze URLs, list formats, and download with a single command. Perfect for scripts and automation.' },
  { icon: '⚡',  title: 'Async Download Queue',       desc: 'Concurrent downloads powered by asyncio. Pause, resume, and cancel any task independently.' },
  { icon: '🗄',  title: 'SQLite State Persistence',   desc: 'All downloads and recent URLs are tracked in a local SQLite DB — no cloud dependency.' },
  { icon: '🔒',  title: 'Path Traversal Protection',  desc: 'Strict filename sanitisation and safe destination-path resolution prevent directory traversal attacks.' },
  { icon: '🎨',  title: 'Dark / Light Themes',        desc: 'Switchable themes with clean QSS stylesheets and consistent design tokens.' },
  { icon: '📦',  title: 'Standalone Executable',      desc: 'Bundle with PyInstaller into a single-file .exe or binary — no Python install required for end users.' },
];

function Features() {
  return (
    <section id="features" className="section">
      <div className="container">
        <div className="section-heading">
          <h2>Everything You Need</h2>
          <p>A complete, production-ready downloader with a clean architecture.</p>
        </div>
        <div className="features-grid">
          {FEATURES.map((f, i) => (
            <div key={f.title} className="feature-card" style={{ animationDelay: `${i * 0.06}s` }}>
              <span className="feature-icon">{f.icon}</span>
              <div className="feature-title">{f.title}</div>
              <div className="feature-desc">{f.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* =============================================
   Supported Sites
   ============================================= */

const SITES = [
  { icon: '▶', name: 'YouTube'   },
  { icon: '🎬', name: 'Vimeo'    },
  { icon: '📸', name: 'Instagram' },
  { icon: '🐦', name: 'Twitter'  },
  { icon: '🎵', name: 'TikTok'   },
  { icon: '📘', name: 'Facebook' },
  { icon: '🔴', name: 'Twitch'   },
  { icon: '💃', name: 'Dailymotion' },
  { icon: '➕', name: '1000+ more' },
];

function SupportedSites() {
  return (
    <section className="section">
      <div className="container">
        <div className="section-heading">
          <h2>Works With All Major Platforms</h2>
          <p>Powered by yt-dlp, which supports over 1 000 websites out of the box.</p>
        </div>
        <div className="sites-row">
          {SITES.map(s => (
            <div key={s.name} className="site-pill">
              <span>{s.icon}</span> {s.name}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* =============================================
   Install Guide
   ============================================= */

const STEPS = [
  { n: 1, title: 'Clone the Repo',      desc: 'git clone the repository to your machine.' },
  { n: 2, title: 'Create a venv',       desc: 'python -m venv .venv && activate it.' },
  { n: 3, title: 'Install deps',        desc: 'pip install -r requirements.txt' },
  { n: 4, title: 'Run',                 desc: 'python main.py for GUI, or use CLI commands.' },
];

const CLI_SNIPPET = `# Analyze a video page
python main.py analyze https://youtube.com/watch?v=...

# Download best format
python main.py download https://youtube.com/watch?v=...

# Download specific format
python main.py download https://youtube.com/watch?v=... --format yt_137`;

function InstallGuide({ showToast }) {
  return (
    <section id="install" className="section">
      <div className="container">
        <div className="section-heading">
          <h2>Get Started in Minutes</h2>
          <p>Works on Windows, macOS, and Linux.</p>
        </div>
        <div className="steps-grid">
          {STEPS.map(s => (
            <div key={s.n} className="step-card">
              <div className="step-num">{s.n}</div>
              <div className="step-title">{s.title}</div>
              <div className="step-desc">{s.desc}</div>
            </div>
          ))}
        </div>

        <br />

        <div className="code-block" style={{ position: 'relative' }}>
          <button
            className="copy-btn"
            onClick={() => copyToClipboard(CLI_SNIPPET, showToast)}
          >
            Copy
          </button>
          <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{CLI_SNIPPET}</pre>
        </div>
      </div>
    </section>
  );
}

/* =============================================
   Footer
   ============================================= */

function Footer() {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-links">
          <a href="https://github.com/AkashDavidKumar/universal-video-downloader-" target="_blank" rel="noreferrer">GitHub</a>
          <a href="https://github.com/AkashDavidKumar/universal-video-downloader-/blob/main/README.md" target="_blank" rel="noreferrer">README</a>
          <a href="https://github.com/AkashDavidKumar/universal-video-downloader-/blob/main/deploy_guide.md" target="_blank" rel="noreferrer">Deploy Guide</a>
          <a href="https://github.com/AkashDavidKumar/universal-video-downloader-/issues" target="_blank" rel="noreferrer">Issues</a>
        </div>
        <p>© {new Date().getFullYear()} Universal Video Downloader — MIT License</p>
        <p style={{ marginTop: '0.3rem', color: 'var(--text-faint)' }}>
          Built with Python · PySide6 · yt-dlp · React · Vite
        </p>
      </div>
    </footer>
  );
}

/* =============================================
   App Root
   ============================================= */

function App() {
  const [demoFocus, setDemoFocus] = useState(false);
  const [globalToast, showGlobalToast] = useToast();

  const handleTryDemo = () => {
    setDemoFocus(true);
    document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <>
      <Navbar />
      <Hero onTryDemo={handleTryDemo} />
      <DownloaderDemo autoFocus={demoFocus} />
      <Features />
      <SupportedSites />
      <InstallGuide showToast={showGlobalToast} />
      <Footer />
      {globalToast && (
        <div className={`toast toast-${globalToast.type}`}>{globalToast.msg}</div>
      )}
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
