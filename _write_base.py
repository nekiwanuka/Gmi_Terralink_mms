import pathlib

content = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{% block title %}GMI ERP{% endblock %}</title>
  <link rel="stylesheet" href="/static/css/site.css" />
</head>
<body>

<header class="topbar">
  <div class="brand">
    {% if profile and profile.logo %}
      <img src="{{ profile.logo.url }}" alt="Logo" class="logo" />
    {% endif %}
    <div>
      <h1>GMI ERP</h1>
      <p>{{ profile.business_name|default:"GMI TERRALINK" }}</p>
    </div>
  </div>
  <div class="topbar-right">
    {% if user.is_authenticated %}
      <span class="role-badge">{{ user_role|default:user.username }}</span>
      <span style="font-size:.85rem;color:#4a5c58">{{ user.username }}</span>
      <a href="/logout/" class="btn btn-secondary btn-sm">Log out</a>
    {% else %}
      <a href="/login/" class="btn btn-primary btn-sm">Log in</a>
    {% endif %}
  </div>
</header>

<div class="layout">
  <nav class="sidebar">
    <span class="nav-section">Main</span>
    <a href="/" {% if request.resolver_match.url_name == 'dashboard' %}class="active"{% endif %}>&#9632; Dashboard</a>

    {% if user_role in "Owner,Finance,Warehouse" %}
    <span class="nav-section">Procurement</span>
    <a href="/procurement/" {% if 'procurement' in request.path %}class="active"{% endif %}>Purchase Orders</a>
    {% endif %}

    {% if user_role in "Owner,Warehouse,Sales,Operations" %}
    <span class="nav-section">Inventory</span>
    <a href="/inventory/" {% if 'inventory' in request.path %}class="active"{% endif %}>Stock Items</a>
    {% endif %}

    {% if user_role in "Owner,Sales,Finance" %}
    <span class="nav-section">Sales</span>
    <a href="/sales/" {% if '/sales/' in request.path %}class="active"{% endif %}>Orders</a>
    {% endif %}

    {% if user_role in "Owner,Finance" %}
    <span class="nav-section">Billing</span>
    <a href="/billing/" {% if '/billing/' in request.path and 'expenses' not in request.path %}class="active"{% endif %}>Invoices</a>
    <a href="/billing/expenses/" {% if 'expenses' in request.path %}class="active"{% endif %}>Expenses</a>
    {% endif %}

    {% if user_role in "Owner,Sales,Finance" %}
    <span class="nav-section">Contacts</span>
    <a href="/contacts/suppliers/" {% if 'suppliers' in request.path %}class="active"{% endif %}>Suppliers</a>
    <a href="/contacts/clients/" {% if 'clients' in request.path %}class="active"{% endif %}>Clients</a>
    {% endif %}

    {% if user_role in "Owner,Operations" %}
    <span class="nav-section">Mining</span>
    <a href="/mining/" {% if '/mining/' in request.path %}class="active"{% endif %}>Production</a>
    {% endif %}

    {% if user_role == "Owner" %}
    <span class="nav-section">System</span>
    <a href="/settings/" {% if request.resolver_match.url_name == 'settings' %}class="active"{% endif %}>Settings</a>
    <a href="/admin/">Admin Panel</a>
    <a href="/api/">API Browser</a>
    {% endif %}
  </nav>

  <div class="content">
    {% if messages %}
      <div class="messages">
        {% for message in messages %}
          <div class="msg {% if message.tags == 'error' %}msg-error{% endif %}">{{ message }}</div>
        {% endfor %}
      </div>
    {% endif %}
    {% block content %}{% endblock %}
  </div>
</div>

{% block extra_js %}{% endblock %}
</body>
</html>
"""

pathlib.Path("templates/base.html").write_text(content, encoding="utf-8")
print("base.html written")
