# Deployment Guide

This project can be hosted in a lightweight way using free-tier services such as Render, Vercel, or similar platforms that support static frontends.

## Recommended approach

- Use the Python backend for actual downloading jobs.
- Use the web frontend in the web/ folder for a simple React-style landing experience.
- Keep the database free by using SQLite locally or a free-tier hosted option only when needed.

## Render

1. Create a new Web Service on Render.
2. Connect this repository.
3. Set the build command to:
   - `pip install -r requirements.txt`
4. Set the start command to:
   - `python main.py`
5. Ensure the service has enough memory for Python and any optional media tooling.

## Vercel

1. Create a new Vercel project from the repository.
2. Set the root directory to `web`.
3. Deploy the static site directly.
4. If a backend endpoint is added later, connect it through a serverless function.

## Notes

- This repository uses SQLite via the local database manager.
- For free-tier hosting, keep the database local to the instance and avoid relying on a managed database.
- For production, consider moving to a managed database only after the app is stable.
