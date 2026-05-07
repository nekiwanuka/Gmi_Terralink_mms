# GMI ERP (GMI TERRALINK)

This is a Django + DRF implementation of the GMI ERP system with Django templates for dashboard/settings/documents and API endpoints for operational workflows.

## Implemented Architecture

1. Django backend for business logic and automation rules.
2. Django REST Framework for API endpoints.
3. Django templates for:
   - Dashboard
   - Settings (business profile + logo upload)
   - Invoice document
   - Receipt document
4. SQLite database for local development.

## Core Modules Included

1. Procurement and import
   - Purchase orders with statuses: Pending, Shipped, In Transit, Arrived.
   - Warehouse receiving updates stock, damaged, and missing quantities.
2. Inventory
   - SKU-based item catalog, stock states, reorder levels.
3. Sales and customer orders
   - Order creation with stock checks and optional no-stock override.
   - Delivery action reduces inventory automatically.
4. Billing and finance
   - Invoice generation from order.
   - Payment recording and auto receipt generation.
   - AR/AP tracking fields and expense records.
5. Contacts
   - Supplier and client records.
   - Client credit limit monitoring.
6. Mining operations
   - Daily production entries and efficiency/cost metrics.
7. Dashboard and alerts
   - KPI snapshot and critical alert summary.
8. Settings-driven documents
   - Business name, address, and logo used directly in invoice/receipt templates.

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run migrations:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
4. Create admin user (optional):
   - `python manage.py createsuperuser`
5. Start server:
   - `python manage.py runserver`

Open:

1. Dashboard: `/`
2. Settings: `/settings/`
3. Admin: `/admin/`
4. API root: `/api/`

## Key API Endpoints

1. `/api/suppliers/`
2. `/api/clients/`
3. `/api/items/`
4. `/api/purchase-orders/`
5. `/api/sales-orders/`
6. `/api/payments/`
7. `/api/payments/with_receipt/`
8. `/api/expenses/`
9. `/api/mining-entries/`

## Note

This repository is Django-first. The old browser-only prototype files were removed so production hosts serve the Django/Passenger app rather than a static `index.html`.
