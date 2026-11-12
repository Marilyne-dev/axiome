# AXIOME

```
axiome/
├── backend/    API Python (FastAPI + SQLite + JWT)  → http://localhost:8000
└── frontend/   Application React (Vite)             → http://localhost:5173
```

## Lancer
Terminal 1 : `cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000`
Terminal 2 : `cd frontend && npm run dev`

## Pages
`/` landing · `/connexion` · `/inscription` · `/espace` (protégée)

## API
`POST /api/auth/register` · `POST /api/auth/login` · `GET /api/auth/me`
`GET /api/content` · `POST /api/analytics/reconcile` · `POST /api/demo` · `GET /api/health`

En production, définissez la variable d'environnement `AXIOME_SECRET` (clé de signature des jetons).
