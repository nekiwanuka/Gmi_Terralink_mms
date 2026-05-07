"""
Passenger WSGI entry point for cPanel "Setup Python App".

cPanel's Phusion Passenger looks for `passenger_wsgi.py` in the
application root and expects an `application` callable.

Steps in cPanel (summary):
1. cPanel → Setup Python App → Create Application
   - Python version: 3.11 (or 3.10+)
   - Application root: gmi_inventory   (the folder you uploaded)
   - Application URL: your domain / subdomain
   - Application startup file: passenger_wsgi.py
   - Application Entry point: application
2. Add environment variables (see .env.example).
3. Open the virtualenv terminal cPanel provides and run:
       pip install -r requirements.txt
       python manage.py migrate
       python manage.py collectstatic --noinput
       python manage.py createsuperuser
4. Click "Restart" on the Python App page after each code change.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Make sure the project is importable
sys.path.insert(0, str(BASE_DIR))

# Optional: load variables from a local .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gmi_erp.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
