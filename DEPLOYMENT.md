# Deployment Guide (Render + Vercel)

## Files Added For Deployment

- .env
- .env.example
- render.yaml
- Procfile
- build.sh
- vercel.json
- runtime.txt

## Environment Variables

Use these variables in both Render and Vercel.

1. SECRET_KEY
   - What it is: Django secret used for sessions and security signing.
   - What to set: a long random string.
   - Quick generator:

     python -c "import secrets; print(secrets.token_urlsafe(64))"

2. DEBUG
   - What it is: enables Django debug mode.
   - What to set in production: False

3. DJANGO_SETTINGS_MODULE
   - What it is: Django settings entrypoint.
   - Value: youtify.settings

4. ALLOWED_HOSTS
   - What it is: allowed domain list for Django host validation.
   - Value format: comma-separated domains with no spaces.
   - Example:

     your-render-name.onrender.com,your-vercel-name.vercel.app

5. DATABASE_URL
   - What it is: database connection string.
   - For production: use PostgreSQL URL.
   - Local development: can stay empty to use sqlite.

## Local Env Setup

1. Open .env and fill values.
2. Keep DEBUG=True only for local use.
3. Keep DATABASE_URL empty locally unless you want local Postgres.
4. Do not commit .env to source control.

## Render Deployment Steps

1. Push this project to GitHub.
2. In Render, click New and choose Blueprint.
3. Select your repository.
4. Render reads render.yaml and creates:
   - a web service
   - a PostgreSQL database
5. In the web service, open Environment and confirm:
   - SECRET_KEY exists
   - DEBUG=False
   - DJANGO_SETTINGS_MODULE=youtify.settings
   - DATABASE_URL is linked from the created database
6. Set ALLOWED_HOSTS to include your Render hostname.
7. Deploy and wait for build to finish.
8. Open your Render URL and test login, signup, search, playlist.

## Vercel Deployment Steps

1. In Vercel, click Add New Project and import this same GitHub repo.
2. Framework can remain Other.
3. vercel.json is already configured to route traffic to youtify/wsgi.py.
4. In Project Settings, add these environment variables:
   - SECRET_KEY
   - DEBUG=False
   - DJANGO_SETTINGS_MODULE=youtify.settings
   - ALLOWED_HOSTS including your Vercel domain
   - DATABASE_URL
5. For DATABASE_URL on Vercel, use one of these:
   - the Render Postgres external connection string
   - or a separate Postgres provider (Neon, Supabase, Vercel Postgres)
6. Trigger deployment.
7. Add the Vercel domain to ALLOWED_HOSTS on both platforms if both are active.

## Important Notes

1. Render is the best host for this full Django app.
2. Vercel works but uses serverless behavior and can have request-time limits.
3. If admin or forms show CSRF errors, confirm ALLOWED_HOSTS values are exact.
