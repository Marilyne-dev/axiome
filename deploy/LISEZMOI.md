# Déploiement AXIOME (production)

1. `python deploy/generer_secrets.py` puis éditer `deploy/.env.production` (domaine, e-mail, clés Stripe/FedaPay, `ANTHROPIC_API_KEY`).
2. `cd deploy && docker compose --env-file .env.production up -d --build`
3. Placer un reverse proxy HTTPS (Caddy, Nginx, Traefik) devant `127.0.0.1:8000` ; servir le front construit (`npm run build` → `front/dist`) sur le même domaine, avec `/api` renvoyé vers le back en retirant le préfixe, et `/missions`, `/vue`, `/console`, `/portail`, `/static`, `/login`, `/logout` renvoyés tels quels vers le back (comme le proxy Vite).

## Ce que l'image contient
LibreOffice (PDF des rapports), Tesseract fra/eng + Poppler (OCR), utilisateur non-root, `HEALTHCHECK` sur `/healthz`.

## Persistance
- `pgdata` : base PostgreSQL. - `storage` : GED, exports TRACFIN, `sanctions/liste.csv`, résultats des tâches de fond. Les deux volumes survivent aux redémarrages et aux mises à jour d'image.

## Sauvegardes
Le service `backup` exécute `backup.sh` chaque jour (dump PostgreSQL + archive des fichiers) vers `BACKUP_DIR` (défaut `deploy/sauvegardes`), rotation `RETENTION_JOURS` (14). **Copiez ce dossier hors du serveur** (autre machine ou stockage objet) : une sauvegarde sur le même disque ne protège pas d'une panne du disque.

Restauration :
```
docker compose exec -T db pg_restore --clean --if-exists --no-owner -U axiome -d axiome < sauvegardes/base_AAAAMMJJ_HHMMSS.dump
docker compose run --rm -v $PWD/sauvegardes:/b api sh -c "tar -xzf /b/fichiers_AAAAMMJJ_HHMMSS.tar.gz -C /data/storage"
```
Testez une restauration sur une machine de test avant d'en avoir besoin.

## Journaux
`LOG_FORMAT=json` : une ligne JSON par événement sur la sortie du conteneur, avec `request_id` (aussi renvoyé dans l'en-tête `X-Request-ID`). Pour les centraliser, branchez le pilote de logs Docker (`fluentd`, `gelf`, `awslogs`…) ou un collecteur (Promtail/Vector) sur les conteneurs.

## Secrets
Le back refuse de démarrer en production avec `SECRET_KEY`, `ADMIN_PASSWORD` ou `SUPERADMIN_PASSWORD` par défaut, `PAYMENT_SANDBOX=true` ou SQLite. Rotation : voir l'en-tête de `generer_secrets.py`.
