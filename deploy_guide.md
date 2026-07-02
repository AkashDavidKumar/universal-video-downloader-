# Deployment Guide — Universal Video Downloader

This guide covers how to host the different parts of this project on free-tier cloud platforms.

> **Architecture note**  
> This project has two independently deployable pieces:
> - **Web frontend** (`web/`) — a static React app (Vite build). Runs anywhere static files can be served.  
> - **Python backend** (`main.py`, `app/`) — a desktop CLI + GUI app. The GUI uses PySide6 (Qt) which **cannot run on any cloud server**. CLI-only mode **can** run on cloud VMs if you skip the GUI.

---

## Part 1 — Deploying the Web Frontend (Static Site)

The React frontend is a pure static site. Build it once and host it for free.

### Build the Frontend

```bash
cd web
npm install
npm run build
# Output: web/dist/
```

---

### Option A — Vercel (Recommended, Easiest)

Vercel auto-detects Vite projects and deploys in under 60 seconds.

**Steps:**

1. Push your project to GitHub (already done — see repo).
2. Go to [vercel.com](https://vercel.com) → **New Project** → Import from GitHub.
3. Select the repository `universal-video-downloader-`.
4. Set these build settings:

   | Setting | Value |
   |---|---|
   | Framework Preset | **Vite** |
   | Root Directory | `web` |
   | Build Command | `npm run build` |
   | Output Directory | `dist` |

5. Click **Deploy**.  
6. Your site is live at `https://your-project.vercel.app`.

**Free tier limits:** 100 GB bandwidth/month, unlimited deployments, custom domain support.

---

### Option B — Netlify

1. Go to [netlify.com](https://netlify.com) → **Add new site** → Import from Git.
2. Connect your GitHub repo.
3. Set build settings:

   | Setting | Value |
   |---|---|
   | Base directory | `web` |
   | Build command | `npm run build` |
   | Publish directory | `web/dist` |

4. Click **Deploy site**.

**Free tier limits:** 100 GB bandwidth/month, 300 build minutes/month.

---

### Option C — GitHub Pages (Zero Config)

1. Build locally:  
   ```bash
   cd web && npm run build
   ```
2. Copy the `web/dist/` contents to a `gh-pages` branch, or use the `gh-pages` npm package:
   ```bash
   npm install -D gh-pages
   # add to web/package.json scripts:
   #   "deploy": "gh-pages -d dist"
   npm run build && npm run deploy
   ```
3. Go to **GitHub → Settings → Pages** → Source: `gh-pages` branch.

**Free tier limits:** Unlimited for public repos.

---

## Part 2 — Deploying the Python CLI (No GUI)

> ⚠️ **PySide6 (desktop GUI) will NOT work on any cloud platform.** Cloud servers have no display. Only CLI mode (`python main.py analyze ...` / `python main.py download ...`) can be hosted.

---

### Option A — Render (Free Web Service)

Render can run a Python CLI as a **background worker** or expose it via a simple HTTP wrapper.

**To add a minimal FastAPI wrapper (optional, not in the current codebase):**

```python
# api_server.py (minimal example, add to project root)
from fastapi import FastAPI
from app.extractors.extractor_manager import ExtractorManager

app = FastAPI()
mgr = ExtractorManager()
mgr.load_all()

@app.get("/analyze")
async def analyze(url: str):
    ext = mgr.get_extractor_for_url(url)
    await ext.analyze(url)
    return {"title": ext.get_title(), "formats": ext.get_available_formats()}
```

**Deploy to Render:**

1. Go to [render.com](https://render.com) → **New Web Service**.
2. Connect your GitHub repo.
3. Set:

   | Setting | Value |
   |---|---|
   | Environment | **Python 3** |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn api_server:app --host 0.0.0.0 --port $PORT` |

4. Set environment variables if needed (e.g. `PYTHONUNBUFFERED=1`).
5. Deploy.

**Free tier limits:** 750 hours/month, spins down after 15 min inactivity.

**Important:** Remove `PySide6` and `pyinstaller` from `requirements.txt` for cloud deploys — they are large and not needed on a server.

---

### Option B — Railway

Railway is the simplest option for running a Python backend.

1. Install the Railway CLI:  
   ```bash
   npm install -g @railway/cli
   railway login
   ```
2. In the project root:  
   ```bash
   railway init
   railway up
   ```
3. Set the start command in `railway.toml`:  
   ```toml
   [deploy]
   startCommand = "python main.py --help"
   ```
4. Add environment variables in the Railway dashboard.

**Free tier limits:** $5 credit/month (≈ 500 hours for a small container).

---

### Option C — Replit (Quick Dev/Demo)

Ideal for showing the CLI to others without any setup.

1. Go to [replit.com](https://replit.com) → **Create Repl** → Import from GitHub.
2. Select the `universal-video-downloader-` repo.
3. In the Shell:
   ```bash
   pip install -r requirements.txt
   python main.py analyze https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```
4. Share the Repl link.

**Free tier limits:** Always-on Repls require a paid plan; free tier sleeps after inactivity.

---

## Database Notes

This project uses **SQLite** stored at `~/.video_downloader_pro/database.db`.

- **On Vercel / Netlify / GitHub Pages** — no database is used (frontend only).
- **On Render / Railway / Replit** — SQLite works but **data is lost on redeploy** unless you mount a persistent disk.
  - Render: add a **Disk** to your service (`/data`), change `DEFAULT_DB_PATH` to `Path("/data/database.db")`.
  - Railway: use a volume mount.
  - For a truly free persistent option, swap the SQLite backend for a free-tier **Turso** (libSQL) or **PlanetScale** database.

---

## Quick Decision Guide

| Goal | Best Option | Cost |
|---|---|---|
| Host the React web UI | Vercel | Free |
| Show the CLI as a demo | Replit | Free |
| Run a real Python API | Render or Railway | Free tier |
| Build a standalone .exe | PyInstaller (local) | Free |
| Full desktop app | Run locally | Free |
