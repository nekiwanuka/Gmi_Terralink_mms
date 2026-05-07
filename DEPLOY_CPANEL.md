# Deploying GMI Inventory to cPanel

This guide walks you through hosting the Django app on shared cPanel hosting
that supports **Setup Python App** (Phusion Passenger).

## 1. What's already in the repo

| File | Purpose |
| --- | --- |
| `passenger_wsgi.py` | Entry point cPanel/Passenger calls |
| `.htaccess` | Security + caching rules |
| `.env.example` | Environment variable template |
| `requirements.txt` | Python dependencies (Django, DRF, Pillow, WhiteNoise, dotenv) |
| `gmi_erp/settings.py` | Reads `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DB_*` from env |

Static files are served by **WhiteNoise** (compressed + hashed in production), so
you don't need to configure Apache aliases.

## 2. Upload the project

Compress the project locally (exclude `.venv/`, `__pycache__/`, `db.sqlite3`,
`media/`, `staticfiles/`, `static/css/site.css.bak`) and upload via cPanel's
**File Manager** or SFTP. Extract into e.g. `/home/<cpaneluser>/gmi_inventory/`.

## 3. Create the Python app in cPanel

cPanel → **Setup Python App** → **Create Application**

| Field | Value |
| --- | --- |
| Python version | 3.11 (or 3.10+) |
| Application root | `gmi_inventory` |
| Application URL | the domain or subdomain you want |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

Click **Create**. cPanel will create a virtualenv and print an
*"Enter to the virtual environment"* command — copy it.

## 4. Configure environment variables

In the same screen click **Add Variable** for each entry from `.env.example`.
At minimum set:

- `DJANGO_SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com`

If you create a MySQL DB in cPanel:

- `DB_ENGINE=django.db.backends.mysql`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD` — exactly as cPanel shows them (they are usually prefixed with your cPanel username, e.g. `cpaneluser_gmi`)
- `DB_HOST=localhost`

Then add `mysqlclient==2.2.4` (or `psycopg2-binary` for Postgres) to
`requirements.txt` — uncomment the line that's already there.

## 5. Install dependencies & migrate

Open **cPanel → Terminal** (or SSH) and paste the *"Enter to the virtual environment"*
command. Then:

```bash
cd ~/gmi_inventory
pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 6. Restart and test

cPanel → Setup Python App → click **Restart** for your application.
Visit `https://yourdomain.com/` — you should see the redesigned login screen.

## 7. Updating the app

After uploading new code:

```bash
cd ~/gmi_inventory
source ~/virtualenv/gmi_inventory/3.11/bin/activate    # or whatever cPanel printed
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then click **Restart** in Setup Python App.

## 8. Notes on database choice

- **SQLite** works fine on cPanel for low-traffic single-tenant deployments — leave `DB_ENGINE` blank. Make sure the `db.sqlite3` file is writable by the cPanel user (`chmod 644` and parent dir `755`).
- **MySQL** is the recommended cPanel default. Use the **MySQL Databases** tool to create the DB + user, grant *ALL PRIVILEGES*, then set the `DB_*` vars.

## 9. Troubleshooting

| Symptom | Fix |
| --- | --- |
| 500 on every page | `tail -n 100 ~/gmi_inventory/stderr.log` (Passenger writes errors here). Usually `DJANGO_ALLOWED_HOSTS` or `STATIC_ROOT` permission. |
| Static files 404 | Re-run `collectstatic` and **Restart** the app. |
| `DisallowedHost` | Add the host to `DJANGO_ALLOWED_HOSTS` env var. |
| `CSRF verification failed` | Add the full `https://...` origin to `DJANGO_CSRF_TRUSTED_ORIGINS`. |
| Changes don't appear | You forgot to **Restart** the Python App. |
