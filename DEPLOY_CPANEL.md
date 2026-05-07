# Deploying GMI Inventory to cPanel

This guide walks you through hosting the Django app on shared cPanel hosting
that supports **Setup Python App** (Phusion Passenger).

## 1. What's already in the repo

| File | Purpose |
| --- | --- |
| `passenger_wsgi.py` | Entry point cPanel/Passenger calls |
| `.htaccess` | Security + caching rules |
| `requirements.txt` | Python dependencies (Django, DRF, Pillow, WhiteNoise, dotenv) |
| `gmi_erp/settings.py` | Reads `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DB_*` from env |

Static files are served by **WhiteNoise** (compressed + hashed in production), so
you don't need to configure Apache aliases.

## 2. Upload the project

Compress the project locally (exclude `.venv/`, `__pycache__/`, `db.sqlite3`,
`media/`, `staticfiles/`, `static/css/site.css.bak`) and upload via cPanel's
**File Manager** or SFTP. Extract into `/home/gmiterralink26/MIMS/`.

## 3. Create the Python app in cPanel

cPanel → **Setup Python App** → **Create Application**

| Field | Value |
| --- | --- |
| Python version | 3.11 (or 3.10+) |
| Application root | `MIMS` |
| Application URL | `mims.gmiterralink.com` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

Click **Create**. cPanel will create a virtualenv and print an
*"Enter to the virtual environment"* command — copy it.

## 4. Create the private `.env` file

Create `/home/gmiterralink26/MIMS/.env` on the server. Do not commit this file
and do not upload it to GitHub.

```bash
source /home/gmiterralink26/virtualenv/MIMS/3.11/bin/activate
cd /home/gmiterralink26/MIMS
nano .env
chmod 600 .env
```

Use this format, replacing the secret/database values with the real cPanel
PostgreSQL credentials:

```env
DJANGO_SECRET_KEY=replace-with-generated-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=mims.gmiterralink.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://mims.gmiterralink.com
DB_ENGINE=django.db.backends.postgresql
DB_NAME=your_cpanel_db_name
DB_USER=your_cpanel_db_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

Generate the secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

`psycopg2-binary` is already in `requirements.txt` so no further driver setup is needed. SQLite is intended for **local development only** and is not used in production.

## 5. Install dependencies & migrate

Open **cPanel → Terminal** (or SSH) and paste the *"Enter to the virtual environment"*
command. Then:

```bash
source /home/gmiterralink26/virtualenv/MIMS/3.11/bin/activate
cd /home/gmiterralink26/MIMS
pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 6. Restart and test

cPanel → Setup Python App → click **Restart** for your application.
Visit `https://mims.gmiterralink.com/` — you should see the redesigned login screen.

## 7. Updating the app

After uploading new code:

```bash
source /home/gmiterralink26/virtualenv/MIMS/3.11/bin/activate
cd /home/gmiterralink26/MIMS
git fetch origin
git reset --hard origin/main
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then click **Restart** in Setup Python App.

## 8. Notes on database choice

- **PostgreSQL (production, required).** Create the database + role in cPanel → **PostgreSQL Databases** (or your managed Postgres provider). Grant the role full privileges on the DB, then set the `DB_*` env vars (engine `django.db.backends.postgresql`, port `5432`). The `psycopg2-binary` driver is bundled in `requirements.txt`.
- **SQLite (development only).** Leave `DB_ENGINE` blank locally and Django falls back to `db.sqlite3` in the project root. Do **not** use SQLite in production — it is excluded from deploys and ignored by git.
- **MySQL (optional alternative).** Supported but not the default. Set `DB_ENGINE=django.db.backends.mysql`, port `3306`, and uncomment `mysqlclient==2.2.4` in `requirements.txt`.

## 9. Troubleshooting

| Symptom | Fix |
| --- | --- |
| 500 on every page | `tail -n 100 /home/gmiterralink26/MIMS/stderr.log` (Passenger writes errors here). Usually `DJANGO_ALLOWED_HOSTS` or `STATIC_ROOT` permission. |
| Static files 404 | Re-run `collectstatic` and **Restart** the app. |
| `DisallowedHost` | Add the host to `DJANGO_ALLOWED_HOSTS` env var. |
| `CSRF verification failed` | Add the full `https://...` origin to `DJANGO_CSRF_TRUSTED_ORIGINS`. |
| Changes don't appear | You forgot to **Restart** the Python App. |
| Old teal dashboard appears | Remove root-level `index.html`, `styles.css`, and `app.js` from the server, then restart the Python App. Those were legacy prototype files and are no longer in the repo. |
