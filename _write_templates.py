"""Create all template files for GMI ERP."""

import pathlib

BASE = pathlib.Path("templates")


def w(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"  wrote {p}")


# ─── Auth ─────────────────────────────────────────────────────────────────────

w(
    "auth/login.html",
    """
{% load static %}
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Login — GMI ERP</title>
  <link rel="stylesheet" href="/static/css/site.css" />
  <style>
    body { display: flex; justify-content: center; align-items: center; min-height: 100vh; }
    .login-box { background:#fff; border:1px solid #d9e0dc; border-radius:14px; padding:32px 36px; width:360px; }
    .login-box h2 { margin-bottom:18px; color:#0b6b5f; }
    .login-box label { display:block; font-size:.83rem; font-weight:600; color:#2d5249; margin-bottom:4px; }
    .login-box input { width:100%; margin-bottom:12px; }
    .login-box button { width:100%; padding:10px; }
  </style>
</head>
<body>
  <div class="login-box">
    <h2>GMI ERP — Sign in</h2>
    {% if messages %}
      {% for m in messages %}<div class="msg {% if m.tags == 'error' %}msg-error{% endif %}">{{ m }}</div>{% endfor %}
    {% endif %}
    {% if form.non_field_errors %}
      <div class="msg msg-error">{{ form.non_field_errors }}</div>
    {% endif %}
    <form method="post">{% csrf_token %}
      <label>Username</label>{{ form.username }}
      <label>Password</label>{{ form.password }}
      <button type="submit" class="btn btn-primary">Sign in</button>
    </form>
  </div>
</body>
</html>
""",
)

w(
    "auth/access_denied.html",
    """
{% extends "base.html" %}
{% block title %}Access Denied — GMI ERP{% endblock %}
{% block content %}
<div class="panel" style="max-width:500px;margin:60px auto;text-align:center">
  <h2 style="color:#b53b3b">&#128274; Access Denied</h2>
  <p style="margin-top:10px">You do not have permission to view this page.</p>
  <a href="/" class="btn btn-primary" style="margin-top:16px">Back to Dashboard</a>
</div>
{% endblock %}
""",
)

# ─── Dashboard ────────────────────────────────────────────────────────────────

w(
    "dashboard.html",
    """
{% extends "base.html" %}
{% block title %}Dashboard — GMI ERP{% endblock %}
{% block content %}
<h2 style="margin-bottom:12px">Dashboard</h2>

<div class="kpis">
  <article>
    <p style="font-size:.78rem;opacity:.8">Total Invoiced</p>
    <h3>UGX {{ total_invoiced|floatformat:0 }}</h3>
  </article>
  <article>
    <p style="font-size:.78rem;opacity:.8">Total Paid</p>
    <h3>UGX {{ total_paid|floatformat:0 }}</h3>
  </article>
  <article>
    <p style="font-size:.78rem;opacity:.8">Outstanding</p>
    <h3>UGX {{ outstanding|floatformat:0 }}</h3>
  </article>
  <article>
    <p style="font-size:.78rem;opacity:.8">Expenses</p>
    <h3>UGX {{ expenses|floatformat:0 }}</h3>
  </article>
  <article>
    <p style="font-size:.78rem;opacity:.8">Supplier Dues</p>
    <h3>UGX {{ supplier_dues|floatformat:0 }}</h3>
  </article>
  <article>
    <p style="font-size:.78rem;opacity:.8">Low-Stock Items</p>
    <h3>{{ low_stock_count }}</h3>
  </article>
  <article>
    <p style="font-size:.78rem;opacity:.8">Month Sales</p>
    <h3>UGX {{ month_sales|floatformat:0 }}</h3>
  </article>
  <article>
    <p style="font-size:.78rem;opacity:.8">Month Output (t)</p>
    <h3>{{ month_output|floatformat:2 }}</h3>
  </article>
</div>

<div class="grid" style="margin-top:16px">
  <div class="panel">
    <h3>Alerts</h3>
    <ul>{% for a in alerts %}<li>{{ a }}</li>{% endfor %}</ul>
  </div>
  <div class="panel">
    <h3>Top Customers</h3>
    <table>
      <thead><tr><th>Client</th><th>Total Invoiced</th></tr></thead>
      <tbody>
        {% for c in top_customers %}
        <tr><td>{{ c.client__name }}</td><td>UGX {{ c.total|floatformat:0 }}</td></tr>
        {% empty %}<tr><td colspan="2">No data</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="panel">
    <h3>Recent Sales Orders</h3>
    <table>
      <thead><tr><th>Code</th><th>Client</th><th>Status</th></tr></thead>
      <tbody>
        {% for o in recent_orders %}
        <tr>
          <td><a href="/sales/{{ o.pk }}/">{{ o.code }}</a></td>
          <td>{{ o.client.name }}</td>
          <td>{{ o.status }}</td>
        </tr>
        {% empty %}<tr><td colspan="3">No orders yet</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="panel">
    <h3>Recent Purchase Orders</h3>
    <table>
      <thead><tr><th>Code</th><th>Supplier</th><th>Status</th></tr></thead>
      <tbody>
        {% for p in recent_pos %}
        <tr>
          <td>{{ p.code }}</td>
          <td>{{ p.supplier.name }}</td>
          <td>{{ p.status }}</td>
        </tr>
        {% empty %}<tr><td colspan="3">No POs yet</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",
)

# ─── Settings ─────────────────────────────────────────────────────────────────

w(
    "settings.html",
    """
{% extends "base.html" %}
{% block title %}Settings — GMI ERP{% endblock %}
{% block content %}
<h2>Settings</h2>
<div class="grid">

  <div class="panel form-panel">
    <h3>Business Profile</h3>
    <form method="post" enctype="multipart/form-data">
      {% csrf_token %}
      <input type="hidden" name="action" value="profile" />
      <div class="form-row">
        <div>
          <label class="form-label">Business Name</label>
          <input name="business_name" value="{{ profile.business_name }}" />
        </div>
      </div>
      <div class="form-row">
        <div>
          <label class="form-label">Business Address</label>
          <textarea name="business_address" rows="3">{{ profile.business_address }}</textarea>
        </div>
      </div>
      <div class="form-row">
        <div>
          <label class="form-label">Logo</label>
          <input type="file" name="logo" accept="image/*" />
          {% if profile.logo %}
            <img src="{{ profile.logo.url }}" class="logo-large" style="margin-top:8px" />
          {% endif %}
        </div>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Save Profile</button>
      </div>
    </form>
  </div>

  <div class="panel">
    <h3>User Roles</h3>
    <table>
      <thead><tr><th>Username</th><th>Current Role</th><th>Change</th></tr></thead>
      <tbody>
        {% for up in users %}
        <tr>
          <td>{{ up.user.username }}</td>
          <td><span class="badge badge-green">{{ up.role }}</span></td>
          <td>
            <form method="post" class="inline-form">
              {% csrf_token %}
              <input type="hidden" name="action" value="role" />
              <input type="hidden" name="user_id" value="{{ up.pk }}" />
              <select name="role">
                {% for val, label in role_choices %}
                  <option value="{{ val }}" {% if val == up.role %}selected{% endif %}>{{ label }}</option>
                {% endfor %}
              </select>
              <button type="submit" class="btn btn-primary btn-sm">Set</button>
            </form>
          </td>
        </tr>
        {% empty %}
        <tr><td colspan="3">No users found</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

</div>
{% endblock %}
""",
)

# ─── Procurement ──────────────────────────────────────────────────────────────

w(
    "procurement/list.html",
    """
{% extends "base.html" %}
{% block title %}Purchase Orders{% endblock %}
{% block content %}
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
  <h2>Purchase Orders</h2>
  {% if user_role in "Owner,Warehouse" %}
  <a href="/procurement/new/" class="btn btn-primary">+ New PO</a>
  {% endif %}
</div>

<div style="margin-bottom:10px">
  <form method="get" class="inline-form">
    <select name="status" onchange="this.form.submit()">
      <option value="">All Statuses</option>
      {% for val, label in status_choices %}
        <option value="{{ val }}" {% if val == current_status %}selected{% endif %}>{{ label }}</option>
      {% endfor %}
    </select>
  </form>
</div>

<div class="panel">
<table>
  <thead>
    <tr>
      <th>Code</th><th>Supplier</th><th>Expected Ship</th><th>Status</th>
      <th>Total</th><th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {% for po in pos %}
    <tr>
      <td>{{ po.code }}</td>
      <td>{{ po.supplier.name }}</td>
      <td>{{ po.expected_shipment_date }}</td>
      <td>
        <span class="badge {% if po.status == 'Arrived' %}badge-green{% elif po.status == 'Pending' %}badge-grey{% else %}badge-yellow{% endif %}">
          {{ po.status }}
        </span>
      </td>
      <td>UGX {{ po.total_amount|floatformat:0 }}</td>
      <td>
        {% if user_role in "Owner,Warehouse" %}
        <form method="post" action="/procurement/{{ po.pk }}/status/" class="inline-form">
          {% csrf_token %}
          <select name="status">
            {% for val, label in status_choices %}
              <option value="{{ val }}" {% if val == po.status %}selected{% endif %}>{{ label }}</option>
            {% endfor %}
          </select>
          <button type="submit" class="btn btn-secondary btn-sm">Update</button>
        </form>
        {% if po.status != 'Arrived' or not po.received_at %}
          &nbsp;<a href="/procurement/{{ po.pk }}/receive/" class="btn btn-primary btn-sm">Receive</a>
        {% endif %}
        {% endif %}
      </td>
    </tr>
    {% empty %}
    <tr><td colspan="6" style="text-align:center;padding:20px">No purchase orders yet.</td></tr>
    {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}
""",
)

w(
    "procurement/create.html",
    """
{% extends "base.html" %}
{% block title %}New Purchase Order{% endblock %}
{% block content %}
<h2>New Purchase Order</h2>
<div class="panel form-panel">
<form method="post">
  {% csrf_token %}
  <div class="form-row">
    <div>
      <label class="form-label">Supplier</label>
      {{ form.supplier }}
      {% if form.supplier.errors %}<span style="color:red">{{ form.supplier.errors }}</span>{% endif %}
    </div>
    <div>
      <label class="form-label">Expected Shipment Date</label>
      {{ form.expected_shipment_date }}
    </div>
  </div>
  <div class="form-row">
    <div>
      <label class="form-label">Bill of Lading</label>
      {{ form.bill_of_lading }}
    </div>
    <div>
      <label class="form-label">Tracking Details</label>
      {{ form.tracking_details }}
    </div>
  </div>

  <h3 style="margin:14px 0 8px">Order Lines</h3>
  <table class="lines-table" id="lines-table">
    <thead>
      <tr><th>#</th><th>Item</th><th>Quantity</th><th>Unit Price (UGX)</th><th></th></tr>
    </thead>
    <tbody id="lines-body">
      <tr>
        <td>1</td>
        <td>
          <select name="line_0_item" class="form-input">
            <option value="">— select item —</option>
            {% for item in items %}
            <option value="{{ item.pk }}">{{ item.sku }} — {{ item.name }}</option>
            {% endfor %}
          </select>
        </td>
        <td><input type="number" name="line_0_qty" min="1" value="1" /></td>
        <td><input type="number" name="line_0_price" step="0.01" min="0" value="0" /></td>
        <td><button type="button" class="btn btn-danger btn-sm" onclick="removeLine(this)">✕</button></td>
      </tr>
    </tbody>
  </table>
  <button type="button" id="add-line" class="btn btn-secondary btn-sm" onclick="addLine()">+ Add Line</button>

  <div class="form-actions">
    <button type="submit" class="btn btn-primary">Create Purchase Order</button>
    <a href="/procurement/" class="btn btn-secondary">Cancel</a>
  </div>
</form>
</div>
{% endblock %}
{% block extra_js %}
<script>
const items = [
  {% for item in items %}
  { pk: {{ item.pk }}, label: "{{ item.sku }} — {{ item.name|escapejs }}" },
  {% endfor %}
];
let lineCount = 1;

function buildItemOptions(sel) {
  sel.innerHTML = '<option value="">— select item —</option>';
  items.forEach(i => {
    const o = document.createElement('option');
    o.value = i.pk; o.textContent = i.label;
    sel.appendChild(o);
  });
}

function addLine() {
  const tbody = document.getElementById('lines-body');
  const idx = lineCount++;
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>${idx + 1}</td>
    <td><select name="line_${idx}_item" class="form-input"></select></td>
    <td><input type="number" name="line_${idx}_qty" min="1" value="1" /></td>
    <td><input type="number" name="line_${idx}_price" step="0.01" min="0" value="0" /></td>
    <td><button type="button" class="btn btn-danger btn-sm" onclick="removeLine(this)">✕</button></td>
  `;
  tbody.appendChild(tr);
  buildItemOptions(tr.querySelector('select'));
}

function removeLine(btn) {
  const tr = btn.closest('tr');
  if (document.querySelectorAll('#lines-body tr').length > 1) tr.remove();
}
</script>
{% endblock %}
""",
)

w(
    "procurement/receive.html",
    """
{% extends "base.html" %}
{% block title %}Receive PO {{ po.code }}{% endblock %}
{% block content %}
<h2>Receive — {{ po.code }}</h2>
<p style="margin-bottom:12px">Supplier: <strong>{{ po.supplier.name }}</strong></p>
<div class="panel">
<form method="post">
  {% csrf_token %}
  <table>
    <thead>
      <tr>
        <th>Item</th><th>Ordered</th>
        <th>Received</th><th>Damaged</th><th>Missing</th>
      </tr>
    </thead>
    <tbody>
      {% for line in po.lines.all %}
      <tr>
        <td>{{ line.item.sku }} — {{ line.item.name }}</td>
        <td>{{ line.quantity }}</td>
        <td><input type="number" name="received_{{ line.pk }}" value="{{ line.quantity }}" min="0" style="width:80px" /></td>
        <td><input type="number" name="damaged_{{ line.pk }}" value="0" min="0" style="width:80px" /></td>
        <td><input type="number" name="missing_{{ line.pk }}" value="0" min="0" style="width:80px" /></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  <div class="form-actions" style="margin-top:14px">
    <button type="submit" class="btn btn-primary">Confirm Receiving</button>
    <a href="/procurement/" class="btn btn-secondary">Cancel</a>
  </div>
</form>
</div>
{% endblock %}
""",
)

# ─── Inventory ────────────────────────────────────────────────────────────────

w(
    "inventory/list.html",
    """
{% extends "base.html" %}
{% block title %}Inventory{% endblock %}
{% block content %}
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
  <h2>Inventory</h2>
  {% if user_role in "Owner,Warehouse" %}
  <a href="/inventory/new/" class="btn btn-primary">+ Add Item</a>
  {% endif %}
</div>

<form method="get" style="margin-bottom:10px;display:flex;gap:8px">
  <input name="q" value="{{ q }}" placeholder="Search by name or SKU…" style="max-width:300px" />
  <button type="submit" class="btn btn-secondary">Search</button>
  {% if q %}<a href="/inventory/" class="btn btn-secondary">Clear</a>{% endif %}
</form>

<div class="panel">
<table>
  <thead>
    <tr>
      <th>SKU</th><th>Name</th><th>Category</th><th>Unit</th>
      <th>On Hand</th><th>Reserved</th><th>Available</th><th>Status</th>
      <th>Reorder Lvl</th><th>Unit Cost</th>
      {% if user_role in "Owner,Warehouse" %}<th></th>{% endif %}
    </tr>
  </thead>
  <tbody>
    {% for item in items %}
    <tr>
      <td>{{ item.sku }}</td>
      <td>{{ item.name }}</td>
      <td>{{ item.category }}</td>
      <td>{{ item.unit }}</td>
      <td>{{ item.stock_on_hand }}</td>
      <td>{{ item.reserved_stock }}</td>
      <td>{{ item.available_stock }}</td>
      <td>
        <span class="badge {% if item.stock_status == 'In Stock' %}badge-green{% elif item.stock_status == 'Low Stock' %}badge-yellow{% else %}badge-red{% endif %}">
          {{ item.stock_status }}
        </span>
      </td>
      <td>{{ item.reorder_level }}</td>
      <td>UGX {{ item.unit_cost|floatformat:0 }}</td>
      {% if user_role in "Owner,Warehouse" %}
      <td><a href="/inventory/{{ item.pk }}/edit/" class="btn btn-secondary btn-sm">Edit</a></td>
      {% endif %}
    </tr>
    {% empty %}
    <tr><td colspan="11" style="text-align:center;padding:20px">No items found.</td></tr>
    {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}
""",
)

w(
    "inventory/form.html",
    """
{% extends "base.html" %}
{% block title %}{{ title }}{% endblock %}
{% block content %}
<h2>{{ title }}</h2>
<div class="panel form-panel">
<form method="post">
  {% csrf_token %}
  <div class="form-row">
    <div>
      <label class="form-label">SKU</label>{{ form.sku }}
      {% if form.sku.errors %}<span style="color:red">{{ form.sku.errors }}</span>{% endif %}
    </div>
    <div>
      <label class="form-label">Name</label>{{ form.name }}
    </div>
  </div>
  <div class="form-row">
    <div><label class="form-label">Category</label>{{ form.category }}</div>
    <div><label class="form-label">Unit</label>{{ form.unit }}</div>
  </div>
  <div class="form-row">
    <div><label class="form-label">Reorder Level</label>{{ form.reorder_level }}</div>
    <div><label class="form-label">Unit Cost (UGX)</label>{{ form.unit_cost }}</div>
  </div>
  <div class="form-actions">
    <button type="submit" class="btn btn-primary">Save</button>
    <a href="/inventory/" class="btn btn-secondary">Cancel</a>
  </div>
</form>
</div>
{% endblock %}
""",
)

# ─── Sales ────────────────────────────────────────────────────────────────────

w(
    "sales/list.html",
    """
{% extends "base.html" %}
{% block title %}Sales Orders{% endblock %}
{% block content %}
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
  <h2>Sales Orders</h2>
  {% if user_role in "Owner,Sales" %}
  <a href="/sales/new/" class="btn btn-primary">+ New Order</a>
  {% endif %}
</div>

<form method="get" style="margin-bottom:10px">
  <select name="status" onchange="this.form.submit()">
    <option value="">All Statuses</option>
    {% for val, label in status_choices %}
      <option value="{{ val }}" {% if val == current_status %}selected{% endif %}>{{ label }}</option>
    {% endfor %}
  </select>
</form>

<div class="panel">
<table>
  <thead>
    <tr>
      <th>Code</th><th>Client</th><th>Status</th><th>Payment</th>
      <th>Est. Delivery</th><th>Actual Delivery</th><th></th>
    </tr>
  </thead>
  <tbody>
    {% for o in orders %}
    <tr>
      <td><a href="/sales/{{ o.pk }}/">{{ o.code }}</a></td>
      <td>{{ o.client.name }}</td>
      <td>
        <span class="badge {% if o.status == 'Delivered' %}badge-green{% elif o.status == 'Pending' %}badge-grey{% else %}badge-yellow{% endif %}">
          {{ o.status }}
        </span>
      </td>
      <td>
        <span class="badge {% if o.payment_status == 'Paid' %}badge-green{% else %}badge-yellow{% endif %}">
          {{ o.payment_status }}
        </span>
      </td>
      <td>{{ o.estimated_delivery_date|default:"—" }}</td>
      <td>{{ o.actual_delivery_date|default:"—" }}</td>
      <td><a href="/sales/{{ o.pk }}/" class="btn btn-secondary btn-sm">View</a></td>
    </tr>
    {% empty %}
    <tr><td colspan="7" style="text-align:center;padding:20px">No orders yet.</td></tr>
    {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}
""",
)

w(
    "sales/create.html",
    """
{% extends "base.html" %}
{% block title %}New Sales Order{% endblock %}
{% block content %}
<h2>New Sales Order</h2>
<div class="panel form-panel">
<form method="post">
  {% csrf_token %}
  <div class="form-row">
    <div>
      <label class="form-label">Client</label>
      <select name="client" class="form-input">
        <option value="">— select client —</option>
        {% for c in clients %}
          <option value="{{ c.pk }}">{{ c.name }}</option>
        {% endfor %}
      </select>
    </div>
    <div>
      <label class="form-label">Est. Delivery Date</label>
      <input type="date" name="estimated_delivery_date" />
    </div>
  </div>
  <div class="form-row">
    <div>
      <label class="form-label">Deposit (UGX)</label>
      <input type="number" name="deposit" value="0" min="0" step="0.01" />
    </div>
    <div style="display:flex;align-items:flex-end;gap:8px;padding-bottom:2px">
      <input type="checkbox" name="allow_no_stock_override" id="override" style="width:auto" />
      <label for="override" style="font-size:.88rem">Allow zero-stock override</label>
    </div>
  </div>

  <h3 style="margin:14px 0 8px">Order Lines</h3>
  <table class="lines-table">
    <thead>
      <tr><th>#</th><th>Item</th><th>Stock</th><th>Qty</th><th>Unit Price (UGX)</th><th></th></tr>
    </thead>
    <tbody id="lines-body">
      <tr>
        <td>1</td>
        <td>
          <select name="line_0_item" id="item_0" onchange="updateStock(0)" class="form-input">
            <option value="">— select item —</option>
            {% for item in items %}
            <option value="{{ item.pk }}" data-stock="{{ item.available_stock }}" data-price="{{ item.unit_cost }}">
              {{ item.sku }} — {{ item.name }}
            </option>
            {% endfor %}
          </select>
        </td>
        <td id="stock_0">—</td>
        <td><input type="number" name="line_0_qty" min="1" value="1" style="width:70px" /></td>
        <td><input type="number" name="line_0_price" step="0.01" min="0" id="price_0" value="0" style="width:110px" /></td>
        <td><button type="button" class="btn btn-danger btn-sm" onclick="removeLine(this)">✕</button></td>
      </tr>
    </tbody>
  </table>
  <button type="button" class="btn btn-secondary btn-sm" id="add-line" onclick="addLine()">+ Add Line</button>

  <div class="form-actions">
    <button type="submit" class="btn btn-primary">Create Order &amp; Invoice</button>
    <a href="/sales/" class="btn btn-secondary">Cancel</a>
  </div>
</form>
</div>
{% endblock %}
{% block extra_js %}
<script>
const itemData = {
  {% for item in items %}
  {{ item.pk }}: { stock: {{ item.available_stock }}, price: "{{ item.unit_cost }}" },
  {% endfor %}
};
const itemOptions = `<option value="">— select item —</option>` +
  [{% for item in items %}
    `<option value="{{ item.pk }}" data-stock="{{ item.available_stock }}" data-price="{{ item.unit_cost }}">{{ item.sku }} — {{ item.name|escapejs }}</option>`,
  {% endfor %}].join('');

let lineCount = 1;

function updateStock(idx) {
  const sel = document.getElementById(`item_${idx}`);
  const pk = sel.value;
  const stockEl = document.getElementById(`stock_${idx}`);
  const priceEl = document.getElementById(`price_${idx}`);
  if (pk && itemData[pk]) {
    stockEl.textContent = itemData[pk].stock;
    priceEl.value = itemData[pk].price;
  } else {
    stockEl.textContent = "—";
  }
}

function addLine() {
  const tbody = document.getElementById('lines-body');
  const idx = lineCount++;
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>${idx + 1}</td>
    <td><select name="line_${idx}_item" id="item_${idx}" onchange="updateStock(${idx})" class="form-input">${itemOptions}</select></td>
    <td id="stock_${idx}">—</td>
    <td><input type="number" name="line_${idx}_qty" min="1" value="1" style="width:70px" /></td>
    <td><input type="number" name="line_${idx}_price" step="0.01" min="0" id="price_${idx}" value="0" style="width:110px" /></td>
    <td><button type="button" class="btn btn-danger btn-sm" onclick="removeLine(this)">✕</button></td>
  `;
  tbody.appendChild(tr);
}

function removeLine(btn) {
  if (document.querySelectorAll('#lines-body tr').length > 1)
    btn.closest('tr').remove();
}
</script>
{% endblock %}
""",
)

w(
    "sales/detail.html",
    """
{% extends "base.html" %}
{% block title %}Order {{ order.code }}{% endblock %}
{% block content %}
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
  <h2>Order {{ order.code }}</h2>
  <a href="/sales/" class="btn btn-secondary btn-sm">← Back</a>
</div>

<div class="grid">
  <div class="panel">
    <h3>Order Details</h3>
    <table>
      <tr><th>Client</th><td>{{ order.client.name }}</td></tr>
      <tr><th>Status</th><td>{{ order.status }}</td></tr>
      <tr><th>Payment</th><td>{{ order.payment_status }}</td></tr>
      <tr><th>Est. Delivery</th><td>{{ order.estimated_delivery_date|default:"—" }}</td></tr>
      <tr><th>Actual Delivery</th><td>{{ order.actual_delivery_date|default:"—" }}</td></tr>
    </table>

    {% if order.status != 'Delivered' and user_role in "Owner,Warehouse,Sales" %}
    <form method="post" action="/sales/{{ order.pk }}/deliver/" style="margin-top:12px">
      {% csrf_token %}
      <button type="submit" class="btn btn-primary">Mark as Delivered</button>
    </form>
    {% endif %}
  </div>

  <div class="panel">
    <h3>Line Items</h3>
    <table>
      <thead><tr><th>Item</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead>
      <tbody>
        {% for line in order.lines.all %}
        <tr>
          <td>{{ line.item.sku }} — {{ line.item.name }}</td>
          <td>{{ line.quantity }}</td>
          <td>{{ line.unit_price|floatformat:0 }}</td>
          <td>{{ line.line_total|floatformat:0 }}</td>
        </tr>
        {% endfor %}
      </tbody>
      <tfoot>
        <tr><th colspan="3">Subtotal</th><th>UGX {{ order.subtotal|floatformat:0 }}</th></tr>
      </tfoot>
    </table>
  </div>

  {% if invoice %}
  <div class="panel">
    <h3>Invoice — {{ invoice.code }}</h3>
    <table>
      <tr><th>Total</th><td>UGX {{ invoice.total_amount|floatformat:0 }}</td></tr>
      <tr><th>Paid</th><td>UGX {{ invoice.paid_amount|floatformat:0 }}</td></tr>
      <tr><th>Balance</th><td>UGX {{ invoice.balance|floatformat:0 }}</td></tr>
    </table>
    <a href="/documents/invoice/{{ invoice.pk }}/" class="btn btn-secondary btn-sm" style="margin-top:8px" target="_blank">Print Invoice</a>

    {% if invoice.balance > 0 and user_role in "Owner,Finance" %}
    <h4 style="margin-top:14px">Record Payment</h4>
    <form method="post" action="/sales/pay/{{ invoice.pk }}/" class="inline-form" style="flex-wrap:wrap;gap:6px">
      {% csrf_token %}
      <input type="number" name="amount" placeholder="Amount (UGX)" min="0.01" step="0.01" style="width:150px" />
      <select name="mode" style="width:auto">
        {% for val, label in payment_modes %}<option value="{{ val }}">{{ label }}</option>{% endfor %}
      </select>
      <button type="submit" class="btn btn-primary btn-sm">Pay</button>
    </form>
    {% endif %}
  </div>

  <div class="panel">
    <h3>Payment History</h3>
    <table>
      <thead><tr><th>Date</th><th>Amount</th><th>Mode</th><th>Receipt</th></tr></thead>
      <tbody>
        {% for pmt in payments %}
        <tr>
          <td>{{ pmt.created_at|date:"d/m/Y" }}</td>
          <td>UGX {{ pmt.amount|floatformat:0 }}</td>
          <td>{{ pmt.mode }}</td>
          <td>
            {% if pmt.receipt %}
            <a href="/documents/receipt/{{ pmt.receipt.pk }}/" class="btn btn-secondary btn-sm" target="_blank">{{ pmt.receipt.code }}</a>
            {% endif %}
          </td>
        </tr>
        {% empty %}
        <tr><td colspan="4">No payments yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}
</div>
{% endblock %}
""",
)

# ─── Billing ──────────────────────────────────────────────────────────────────

w(
    "billing/overview.html",
    """
{% extends "base.html" %}
{% block title %}Billing{% endblock %}
{% block content %}
<h2>Billing — Invoices</h2>
<div class="kpis" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-bottom:16px">
  <article><p style="font-size:.78rem;opacity:.8">Total Invoiced</p><h3>UGX {{ total_invoiced|floatformat:0 }}</h3></article>
  <article><p style="font-size:.78rem;opacity:.8">Total Paid</p><h3>UGX {{ total_paid|floatformat:0 }}</h3></article>
  <article><p style="font-size:.78rem;opacity:.8">Outstanding</p><h3>UGX {{ total_balance|floatformat:0 }}</h3></article>
</div>

<div class="panel">
<table>
  <thead>
    <tr>
      <th>Invoice</th><th>Client</th><th>Order</th><th>Total</th>
      <th>Paid</th><th>Balance</th><th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {% for inv in invoices %}
    <tr>
      <td>{{ inv.code }}</td>
      <td>{{ inv.client.name }}</td>
      <td><a href="/sales/{{ inv.sales_order.pk }}/">{{ inv.sales_order.code }}</a></td>
      <td>UGX {{ inv.total_amount|floatformat:0 }}</td>
      <td>UGX {{ inv.paid_amount|floatformat:0 }}</td>
      <td>
        <span class="badge {% if inv.balance == 0 %}badge-green{% else %}badge-red{% endif %}">
          UGX {{ inv.balance|floatformat:0 }}
        </span>
      </td>
      <td>
        <a href="/documents/invoice/{{ inv.pk }}/" class="btn btn-secondary btn-sm" target="_blank">Print</a>
        {% if inv.balance > 0 %}
        <form method="post" action="/billing/pay/{{ inv.pk }}/" class="inline-form" style="margin-top:4px">
          {% csrf_token %}
          <input type="number" name="amount" placeholder="Amount" min="0.01" step="0.01" style="width:120px" />
          <select name="mode" style="width:auto">
            {% for val, label in payment_modes %}<option value="{{ val }}">{{ label }}</option>{% endfor %}
          </select>
          <button type="submit" class="btn btn-primary btn-sm">Pay</button>
        </form>
        {% endif %}
      </td>
    </tr>
    {% empty %}
    <tr><td colspan="7" style="text-align:center;padding:20px">No invoices yet.</td></tr>
    {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}
""",
)

w(
    "billing/expenses.html",
    """
{% extends "base.html" %}
{% block title %}Expenses{% endblock %}
{% block content %}
<h2>Expenses</h2>
<div class="grid">
  <div class="panel form-panel">
    <h3>Record Expense</h3>
    <form method="post">
      {% csrf_token %}
      <div class="form-row">
        <div><label class="form-label">Type</label>{{ form.expense_type }}</div>
        <div><label class="form-label">Supplier (optional)</label>{{ form.supplier }}</div>
      </div>
      <div class="form-row">
        <div><label class="form-label">Amount (UGX)</label>{{ form.amount }}</div>
        <div><label class="form-label">Notes</label>{{ form.notes }}</div>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Save Expense</button>
      </div>
    </form>
  </div>

  <div class="panel">
    <h3>Expenses (Total: UGX {{ total|floatformat:0 }})</h3>
    <table>
      <thead><tr><th>Date</th><th>Type</th><th>Supplier</th><th>Amount</th><th>Notes</th></tr></thead>
      <tbody>
        {% for e in expenses %}
        <tr>
          <td>{{ e.created_at|date:"d/m/Y" }}</td>
          <td>{{ e.expense_type }}</td>
          <td>{{ e.supplier.name|default:"—" }}</td>
          <td>UGX {{ e.amount|floatformat:0 }}</td>
          <td>{{ e.notes|default:"—" }}</td>
        </tr>
        {% empty %}
        <tr><td colspan="5">No expenses yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",
)

# ─── Contacts ─────────────────────────────────────────────────────────────────

w(
    "contacts/suppliers.html",
    """
{% extends "base.html" %}
{% block title %}Suppliers{% endblock %}
{% block content %}
<h2>Suppliers</h2>
<div class="grid">
  <div class="panel form-panel">
    <h3>Add Supplier</h3>
    <form method="post">
      {% csrf_token %}
      <div class="form-row">
        <div><label class="form-label">Name</label>{{ form.name }}</div>
        <div><label class="form-label">Country</label>{{ form.country }}</div>
      </div>
      <div class="form-row">
        <div><label class="form-label">Contact Person</label>{{ form.contact_person }}</div>
        <div><label class="form-label">Payment Terms</label>{{ form.payment_terms }}</div>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Add Supplier</button>
      </div>
    </form>
  </div>

  <div class="panel">
    <h3>All Suppliers</h3>
    <table>
      <thead><tr><th>Name</th><th>Country</th><th>Contact</th><th>Terms</th><th></th></tr></thead>
      <tbody>
        {% for s in suppliers %}
        <tr>
          <td>{{ s.name }}</td>
          <td>{{ s.country }}</td>
          <td>{{ s.contact_person }}</td>
          <td>{{ s.payment_terms }}</td>
          <td><a href="/contacts/suppliers/{{ s.pk }}/edit/" class="btn btn-secondary btn-sm">Edit</a></td>
        </tr>
        {% empty %}
        <tr><td colspan="5">No suppliers yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",
)

w(
    "contacts/supplier_form.html",
    """
{% extends "base.html" %}
{% block title %}Edit {{ supplier.name }}{% endblock %}
{% block content %}
<h2>Edit Supplier — {{ supplier.name }}</h2>
<div class="panel form-panel">
<form method="post">
  {% csrf_token %}
  <div class="form-row">
    <div><label class="form-label">Name</label>{{ form.name }}</div>
    <div><label class="form-label">Country</label>{{ form.country }}</div>
  </div>
  <div class="form-row">
    <div><label class="form-label">Contact Person</label>{{ form.contact_person }}</div>
    <div><label class="form-label">Payment Terms</label>{{ form.payment_terms }}</div>
  </div>
  <div class="form-actions">
    <button type="submit" class="btn btn-primary">Save</button>
    <a href="/contacts/suppliers/" class="btn btn-secondary">Cancel</a>
  </div>
</form>
</div>
{% endblock %}
""",
)

w(
    "contacts/clients.html",
    """
{% extends "base.html" %}
{% block title %}Clients{% endblock %}
{% block content %}
<h2>Clients</h2>
<div class="grid">
  <div class="panel form-panel">
    <h3>Add Client</h3>
    <form method="post">
      {% csrf_token %}
      <div class="form-row">
        <div><label class="form-label">Name</label>{{ form.name }}</div>
        <div><label class="form-label">Phone</label>{{ form.phone }}</div>
      </div>
      <div class="form-row">
        <div><label class="form-label">Email</label>{{ form.email }}</div>
        <div><label class="form-label">Credit Limit (UGX)</label>{{ form.credit_limit }}</div>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Add Client</button>
      </div>
    </form>
  </div>

  <div class="panel">
    <h3>All Clients</h3>
    <table>
      <thead><tr><th>Name</th><th>Phone</th><th>Email</th><th>Credit Limit</th><th>Outstanding</th><th></th></tr></thead>
      <tbody>
        {% for c in clients %}
        <tr>
          <td>{{ c.name }}</td>
          <td>{{ c.phone }}</td>
          <td>{{ c.email }}</td>
          <td>UGX {{ c.credit_limit|floatformat:0 }}</td>
          <td>UGX {{ c.outstanding_balance|floatformat:0 }}</td>
          <td><a href="/contacts/clients/{{ c.pk }}/edit/" class="btn btn-secondary btn-sm">Edit</a></td>
        </tr>
        {% empty %}
        <tr><td colspan="6">No clients yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",
)

w(
    "contacts/client_form.html",
    """
{% extends "base.html" %}
{% block title %}Edit {{ client.name }}{% endblock %}
{% block content %}
<h2>Edit Client — {{ client.name }}</h2>
<div class="panel form-panel">
<form method="post">
  {% csrf_token %}
  <div class="form-row">
    <div><label class="form-label">Name</label>{{ form.name }}</div>
    <div><label class="form-label">Phone</label>{{ form.phone }}</div>
  </div>
  <div class="form-row">
    <div><label class="form-label">Email</label>{{ form.email }}</div>
    <div><label class="form-label">Credit Limit (UGX)</label>{{ form.credit_limit }}</div>
  </div>
  <div class="form-actions">
    <button type="submit" class="btn btn-primary">Save</button>
    <a href="/contacts/clients/" class="btn btn-secondary">Cancel</a>
  </div>
</form>
</div>
{% endblock %}
""",
)

# ─── Mining ───────────────────────────────────────────────────────────────────

w(
    "mining/list.html",
    """
{% extends "base.html" %}
{% block title %}Mining — Production{% endblock %}
{% block content %}
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
  <h2>Mining — Production Entries</h2>
  <a href="/mining/new/" class="btn btn-primary">+ Log Entry</a>
</div>

<form method="get" style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
  <label class="form-label" style="margin-bottom:0">Filter Month:</label>
  <input type="month" name="month" value="{{ month }}" />
  <button type="submit" class="btn btn-secondary btn-sm">Filter</button>
  {% if month %}<a href="/mining/" class="btn btn-secondary btn-sm">Clear</a>{% endif %}
</form>

<div class="kpis" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-bottom:16px">
  <article>
    <p style="font-size:.78rem;opacity:.8">Total Produced (t)</p>
    <h3>{{ totals.total_produced|default:0|floatformat:2 }}</h3>
  </article>
  <article>
    <p style="font-size:.78rem;opacity:.8">Total Hours</p>
    <h3>{{ totals.total_hours|default:0|floatformat:1 }}</h3>
  </article>
  <article>
    <p style="font-size:.78rem;opacity:.8">Total Labor Cost</p>
    <h3>UGX {{ totals.total_labor|default:0|floatformat:0 }}</h3>
  </article>
</div>

<div class="panel">
<table>
  <thead>
    <tr>
      <th>Date</th><th>Mineral</th><th>Line</th><th>Produced (t)</th>
      <th>Hours</th><th>Output/Hr</th><th>Staff</th><th>Expats</th>
      <th>Labor Cost</th><th>Cost/t</th>
    </tr>
  </thead>
  <tbody>
    {% for e in entries %}
    <tr>
      <td>{{ e.date }}</td>
      <td>{{ e.mineral_type }}</td>
      <td>{{ e.production_line }}</td>
      <td>{{ e.quantity_produced|floatformat:2 }}</td>
      <td>{{ e.hours_worked|floatformat:1 }}</td>
      <td>{{ e.output_per_hour|floatformat:3 }}</td>
      <td>{{ e.line_staff_count }}</td>
      <td>{{ e.expatriates_count }}</td>
      <td>UGX {{ e.labor_cost|floatformat:0 }}</td>
      <td>UGX {{ e.cost_per_output|floatformat:0 }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="10" style="text-align:center;padding:20px">No entries found.</td></tr>
    {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}
""",
)

w(
    "mining/create.html",
    """
{% extends "base.html" %}
{% block title %}Log Production Entry{% endblock %}
{% block content %}
<h2>Log Production Entry</h2>
<div class="panel form-panel">
<form method="post">
  {% csrf_token %}
  <div class="form-row">
    <div><label class="form-label">Date</label>{{ form.date }}</div>
    <div><label class="form-label">Mineral Type</label>{{ form.mineral_type }}</div>
  </div>
  <div class="form-row">
    <div><label class="form-label">Production Line</label>{{ form.production_line }}</div>
    <div><label class="form-label">Quantity Produced (t)</label>{{ form.quantity_produced }}</div>
  </div>
  <div class="form-row">
    <div><label class="form-label">Hours Worked</label>{{ form.hours_worked }}</div>
    <div><label class="form-label">Line Staff Count</label>{{ form.line_staff_count }}</div>
  </div>
  <div class="form-row">
    <div><label class="form-label">Expatriates Count</label>{{ form.expatriates_count }}</div>
    <div><label class="form-label">Labor Cost (UGX)</label>{{ form.labor_cost }}</div>
  </div>
  <div class="form-actions">
    <button type="submit" class="btn btn-primary">Save Entry</button>
    <a href="/mining/" class="btn btn-secondary">Cancel</a>
  </div>
</form>
</div>
{% endblock %}
""",
)

print("\nAll templates created successfully.")
