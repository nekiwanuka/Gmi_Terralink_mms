const STORAGE_KEY = "gmi_erp_db_v1";

const defaultDb = {
  settings: {
    businessName: "GMI TERRALINK",
    businessAddress: "Kampala, Uganda",
    logoData: ""
  },
  suppliers: [],
  clients: [],
  items: [],
  purchaseOrders: [],
  orders: [],
  invoices: [],
  payments: [],
  receipts: [],
  expenses: [],
  miningEntries: []
};

let db = loadDb();
let poDraftLines = [];
let orderDraftLines = [];

init();

function init() {
  bindTabs();
  bindForms();
  setToday();
  seedIfEmpty();
  refreshAll();
}

function loadDb() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : structuredClone(defaultDb);
  } catch (_err) {
    return structuredClone(defaultDb);
  }
}

function saveDb() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
}

function uid(prefix) {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 10000)}`;
}

function money(n) {
  const amount = Number(n || 0);
  return `UGX ${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function day(d) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString();
}

function setToday() {
  const node = qs("#todayDate");
  node.textContent = new Date().toLocaleDateString(undefined, {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
}

function bindTabs() {
  qsa(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      qsa(".tab").forEach((b) => b.classList.remove("active"));
      qsa(".tab-pane").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      qs(`#${btn.dataset.tab}`).classList.add("active");
    });
  });
}

function bindForms() {
  qs("#supplierForm").addEventListener("submit", onSupplierSubmit);
  qs("#clientForm").addEventListener("submit", onClientSubmit);
  qs("#itemForm").addEventListener("submit", onItemSubmit);

  qs("#addPoLine").addEventListener("click", addPoLine);
  qs("#poForm").addEventListener("submit", onPoSubmit);
  qs("#receivingPo").addEventListener("change", renderReceivingLines);
  qs("#receivingForm").addEventListener("submit", onReceivingSubmit);

  qs("#addOrderLine").addEventListener("click", addOrderLine);
  qs("#orderForm").addEventListener("submit", onOrderSubmit);

  qs("#paymentForm").addEventListener("submit", onPaymentSubmit);
  qs("#expenseForm").addEventListener("submit", onExpenseSubmit);

  qs("#miningForm").addEventListener("submit", onMiningSubmit);

  qs("#settingsForm").addEventListener("submit", onSettingsSubmit);
}

function seedIfEmpty() {
  if (db.suppliers.length || db.clients.length || db.items.length) return;

  db.suppliers.push(
    {
      id: uid("sup"),
      name: "Shandong Mine Parts Co.",
      country: "China",
      contactPerson: "Li Wei",
      paymentTerms: "30% upfront, 70% before dispatch"
    },
    {
      id: uid("sup"),
      name: "Kampala Logistics Hub",
      country: "Uganda",
      contactPerson: "David Okello",
      paymentTerms: "Net 15"
    }
  );

  db.clients.push(
    {
      id: uid("cli"),
      name: "Nyota Mining Ltd",
      phone: "+256700100100",
      email: "ops@nyota.example",
      creditLimit: 50000000
    },
    {
      id: uid("cli"),
      name: "Mamba Quarry",
      phone: "+256700200200",
      email: "procurement@mamba.example",
      creditLimit: 15000000
    }
  );

  db.items.push(
    {
      id: uid("itm"),
      sku: "DRL-BIT-06",
      name: "Drill Bit 6-inch",
      category: "Drilling",
      unit: "Piece",
      reorderLevel: 8,
      unitCost: 850000,
      stockOnHand: 18,
      reserved: 2,
      sold: 30
    },
    {
      id: uid("itm"),
      sku: "CRSH-BRG-22",
      name: "Crusher Bearing Type-22",
      category: "Crushing",
      unit: "Set",
      reorderLevel: 4,
      unitCost: 2200000,
      stockOnHand: 3,
      reserved: 0,
      sold: 11
    }
  );

  saveDb();
}

function refreshAll() {
  saveDb();
  renderHeaderSettings();
  fillSelects();

  renderSuppliers();
  renderClients();
  renderInventory();
  renderPoLines();
  renderPoTable();
  renderReceivingPoOptions();
  renderReceivingLines();
  renderOrderLines();
  renderOrders();
  renderInvoices();
  renderReceipts();
  renderMining();
  renderDashboard();
  renderSettingsPreview();
}

function fillSelects() {
  fillSelect("#poSupplier", db.suppliers, "name");
  fillSelect("#orderClient", db.clients, "name");
  fillSelect("#poItem", db.items, (x) => `${x.sku} - ${x.name}`);
  fillSelect("#orderItem", db.items, (x) => `${x.sku} - ${x.name}`);
  fillSelect("#expenseSupplier", [{ id: "", name: "-" }, ...db.suppliers], "name");

  const invoiceOpts = db.invoices.map((x) => ({
    id: x.id,
    name: `${x.code} | Balance: ${money(invoiceBalance(x.id))}`
  }));
  fillSelect("#paymentInvoice", invoiceOpts, "name");
}

function fillSelect(selector, arr, labelGetter) {
  const sel = qs(selector);
  sel.innerHTML = "";
  if (!arr.length) {
    const op = document.createElement("option");
    op.value = "";
    op.textContent = "No data";
    sel.appendChild(op);
    return;
  }
  arr.forEach((item) => {
    const op = document.createElement("option");
    op.value = item.id;
    op.textContent = typeof labelGetter === "function" ? labelGetter(item) : item[labelGetter];
    sel.appendChild(op);
  });
}

function onSupplierSubmit(e) {
  e.preventDefault();
  db.suppliers.push({
    id: uid("sup"),
    name: val("#supplierName"),
    country: val("#supplierCountry"),
    contactPerson: val("#supplierContact"),
    paymentTerms: val("#supplierTerms")
  });
  e.target.reset();
  refreshAll();
}

function onClientSubmit(e) {
  e.preventDefault();
  db.clients.push({
    id: uid("cli"),
    name: val("#clientName"),
    phone: val("#clientPhone"),
    email: val("#clientEmail"),
    creditLimit: num("#clientCredit")
  });
  e.target.reset();
  refreshAll();
}

function onItemSubmit(e) {
  e.preventDefault();
  const sku = val("#itemSku").trim();
  const existing = db.items.find((x) => x.sku.toLowerCase() === sku.toLowerCase());
  if (existing) {
    existing.name = val("#itemName");
    existing.category = val("#itemCategory");
    existing.unit = val("#itemUnit");
    existing.reorderLevel = num("#itemReorder");
    existing.unitCost = num("#itemCost");
  } else {
    db.items.push({
      id: uid("itm"),
      sku,
      name: val("#itemName"),
      category: val("#itemCategory"),
      unit: val("#itemUnit"),
      reorderLevel: num("#itemReorder"),
      unitCost: num("#itemCost"),
      stockOnHand: 0,
      reserved: 0,
      sold: 0
    });
  }
  e.target.reset();
  refreshAll();
}

function addPoLine() {
  const itemId = val("#poItem");
  if (!itemId) return;
  poDraftLines.push({
    itemId,
    qty: num("#poQty"),
    unitPrice: num("#poPrice")
  });
  qs("#poQty").value = "";
  qs("#poPrice").value = "";
  renderPoLines();
}

function renderPoLines() {
  const wrap = qs("#poLines");
  if (!poDraftLines.length) {
    wrap.innerHTML = '<p class="subtle">No lines added yet.</p>';
    return;
  }
  wrap.innerHTML = poDraftLines
    .map((line, i) => {
      const it = findById(db.items, line.itemId);
      return `<div class="row">
        <span>${it ? it.sku : "Unknown"} x ${line.qty} @ ${money(line.unitPrice)}</span>
        <button type="button" class="ghost" data-po-line-remove="${i}">Remove</button>
      </div>`;
    })
    .join("");

  qsa("[data-po-line-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      poDraftLines.splice(Number(btn.dataset.poLineRemove), 1);
      renderPoLines();
    });
  });
}

function onPoSubmit(e) {
  e.preventDefault();
  if (!poDraftLines.length) return alert("Add at least one PO line.");

  db.purchaseOrders.push({
    id: uid("po"),
    code: `PO-${Date.now().toString().slice(-6)}`,
    supplierId: val("#poSupplier"),
    expectedShipmentDate: val("#poExpectedDate"),
    status: "Pending",
    billOfLading: "",
    trackingDetails: "",
    lines: poDraftLines.map((x) => ({ ...x })),
    createdAt: new Date().toISOString(),
    receivedAt: null
  });

  poDraftLines = [];
  e.target.reset();
  refreshAll();
}

function renderPoTable() {
  const wrap = qs("#poTable");
  if (!db.purchaseOrders.length) {
    wrap.innerHTML = '<p class="subtle">No purchase orders yet.</p>';
    return;
  }

  wrap.innerHTML = `<table class="table">
    <thead>
      <tr>
        <th>PO</th>
        <th>Supplier</th>
        <th>Status</th>
        <th>Expected</th>
        <th>Tracking</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      ${db.purchaseOrders
        .map((po) => {
          const supplier = findById(db.suppliers, po.supplierId);
          return `<tr>
            <td>${po.code}</td>
            <td>${supplier ? supplier.name : "-"}</td>
            <td>
              <select data-po-status="${po.id}">
                ${["Pending", "Shipped", "In Transit", "Arrived"]
                  .map((s) => `<option ${po.status === s ? "selected" : ""}>${s}</option>`)
                  .join("")}
              </select>
            </td>
            <td>${day(po.expectedShipmentDate)}</td>
            <td>
              <input data-po-track="${po.id}" value="${po.trackingDetails || ""}" placeholder="BL / Tracking" />
            </td>
            <td><button type="button" class="ghost" data-po-save="${po.id}">Save</button></td>
          </tr>`;
        })
        .join("")}
    </tbody>
  </table>`;

  qsa("[data-po-save]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const poId = btn.dataset.poSave;
      const po = findById(db.purchaseOrders, poId);
      const statusSel = qs(`[data-po-status="${poId}"]`);
      const trackInput = qs(`[data-po-track="${poId}"]`);
      const prev = po.status;
      po.status = statusSel.value;
      po.trackingDetails = trackInput.value.trim();
      if (po.status === "Arrived" && prev !== "Arrived") {
        pushSystemAlert(`Shipment ${po.code} arrived in Uganda. Complete warehouse receiving now.`, "good");
      }
      refreshAll();
    });
  });
}

function renderReceivingPoOptions() {
  const arrivedNotReceived = db.purchaseOrders.filter((po) => po.status === "Arrived" && !po.receivedAt);
  fillSelect("#receivingPo", arrivedNotReceived, (x) => `${x.code} (${day(x.expectedShipmentDate)})`);
}

function renderReceivingLines() {
  const poId = val("#receivingPo");
  const po = findById(db.purchaseOrders, poId);
  const wrap = qs("#receivingLines");

  if (!po) {
    wrap.innerHTML = '<p class="subtle">No arrived shipment awaiting receiving.</p>';
    return;
  }

  wrap.innerHTML = po.lines
    .map((line, idx) => {
      const it = findById(db.items, line.itemId);
      return `<div class="row">
        <div>
          <strong>${it ? it.sku : "Unknown"}</strong>
          <div class="subtle">Ordered: ${line.qty}</div>
        </div>
        <div style="display:flex; gap:6px;">
          <input data-rec-qty="${idx}" type="number" min="0" value="${line.qty}" placeholder="Received" style="width:110px;" />
          <input data-rec-dmg="${idx}" type="number" min="0" value="0" placeholder="Damaged" style="width:100px;" />
          <input data-rec-miss="${idx}" type="number" min="0" value="0" placeholder="Missing" style="width:100px;" />
        </div>
      </div>`;
    })
    .join("");
}

function onReceivingSubmit(e) {
  e.preventDefault();
  const poId = val("#receivingPo");
  const po = findById(db.purchaseOrders, poId);
  if (!po) return;

  po.lines.forEach((line, idx) => {
    const received = parseInt(qs(`[data-rec-qty="${idx}"]`).value || "0", 10);
    const damaged = parseInt(qs(`[data-rec-dmg="${idx}"]`).value || "0", 10);
    const missing = parseInt(qs(`[data-rec-miss="${idx}"]`).value || "0", 10);
    const net = Math.max(0, received - damaged - missing);
    const item = findById(db.items, line.itemId);
    if (item) {
      item.stockOnHand += net;
      item.unitCost = line.unitPrice || item.unitCost;
    }
    line.receivedQty = received;
    line.damagedQty = damaged;
    line.missingQty = missing;
  });

  po.receivedAt = new Date().toISOString();
  pushSystemAlert(`Inventory auto-updated from shipment ${po.code}.`, "good");
  refreshAll();
}

function addOrderLine() {
  const itemId = val("#orderItem");
  if (!itemId) return;
  orderDraftLines.push({
    itemId,
    qty: num("#orderQty"),
    unitPrice: num("#orderPrice")
  });
  qs("#orderQty").value = "";
  qs("#orderPrice").value = "";
  renderOrderLines();
}

function renderOrderLines() {
  const wrap = qs("#orderLines");
  if (!orderDraftLines.length) {
    wrap.innerHTML = '<p class="subtle">No lines added yet.</p>';
    return;
  }
  wrap.innerHTML = orderDraftLines
    .map((line, i) => {
      const it = findById(db.items, line.itemId);
      return `<div class="row">
        <span>${it ? it.sku : "Unknown"} x ${line.qty} @ ${money(line.unitPrice)}</span>
        <button type="button" class="ghost" data-order-line-remove="${i}">Remove</button>
      </div>`;
    })
    .join("");

  qsa("[data-order-line-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      orderDraftLines.splice(Number(btn.dataset.orderLineRemove), 1);
      renderOrderLines();
    });
  });
}

function onOrderSubmit(e) {
  e.preventDefault();
  if (!orderDraftLines.length) return alert("Add at least one order line.");

  const allowOverride = qs("#orderOverride").checked;
  const noStockItems = orderDraftLines.filter((line) => availableStock(line.itemId) <= 0);
  if (noStockItems.length && !allowOverride) {
    return alert("Cannot proceed: One or more items have zero available stock. Use override if needed.");
  }

  const fullyAvailable = canFulfill(orderDraftLines);
  if (fullyAvailable) reserveOrderLines(orderDraftLines);

  const subtotal = orderDraftLines.reduce((acc, x) => acc + x.qty * x.unitPrice, 0);
  const deposit = num("#orderDeposit");

  const order = {
    id: uid("ord"),
    code: `SO-${Date.now().toString().slice(-6)}`,
    clientId: val("#orderClient"),
    lines: orderDraftLines.map((x) => ({ ...x })),
    estimatedDeliveryDate: val("#orderEta"),
    actualDeliveryDate: null,
    status: fullyAvailable ? "Processing" : "Awaiting Stock",
    createdAt: new Date().toISOString(),
    subtotal,
    paymentStatus: deposit >= subtotal ? "Paid" : "Partially Paid"
  };

  db.orders.push(order);

  const invoice = {
    id: uid("inv"),
    code: `INV-${Date.now().toString().slice(-6)}`,
    orderId: order.id,
    clientId: order.clientId,
    total: subtotal,
    issuedAt: new Date().toISOString()
  };
  db.invoices.push(invoice);

  if (deposit > 0) {
    createPayment(invoice.id, deposit, "Cash");
  }

  orderDraftLines = [];
  e.target.reset();
  refreshAll();
}

function renderOrders() {
  const wrap = qs("#ordersTable");
  if (!db.orders.length) {
    wrap.innerHTML = '<p class="subtle">No customer orders yet.</p>';
    return;
  }

  wrap.innerHTML = `<table class="table">
    <thead>
      <tr>
        <th>Order</th>
        <th>Client</th>
        <th>Status</th>
        <th>Payment</th>
        <th>ETA</th>
        <th>Actual</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      ${db.orders
        .map((order) => {
          const client = findById(db.clients, order.clientId);
          return `<tr>
            <td>${order.code}</td>
            <td>${client ? client.name : "-"}</td>
            <td>${statusBadge(order.status)}</td>
            <td>${statusBadge(order.paymentStatus)}</td>
            <td>${day(order.estimatedDeliveryDate)}</td>
            <td>${day(order.actualDeliveryDate)}</td>
            <td>
              <button type="button" class="ghost" data-order-deliver="${order.id}">Mark Delivered</button>
              <button type="button" class="ghost" data-order-invoice="${order.id}">Open Invoice</button>
            </td>
          </tr>`;
        })
        .join("")}
    </tbody>
  </table>`;

  qsa("[data-order-deliver]").forEach((btn) => {
    btn.addEventListener("click", () => markDelivered(btn.dataset.orderDeliver));
  });

  qsa("[data-order-invoice]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const order = findById(db.orders, btn.dataset.orderInvoice);
      const invoice = db.invoices.find((inv) => inv.orderId === order.id);
      if (invoice) openInvoiceDoc(invoice.id);
    });
  });
}

function markDelivered(orderId) {
  const order = findById(db.orders, orderId);
  if (!order || order.status === "Delivered") return;

  if (order.status === "Awaiting Stock") {
    if (!canFulfill(order.lines)) {
      return alert("Still insufficient stock to deliver this order.");
    }
    reserveOrderLines(order.lines);
  }

  order.lines.forEach((line) => {
    const item = findById(db.items, line.itemId);
    if (!item) return;
    item.reserved = Math.max(0, item.reserved - line.qty);
    item.stockOnHand = Math.max(0, item.stockOnHand - line.qty);
    item.sold += line.qty;
  });

  order.status = "Delivered";
  order.actualDeliveryDate = new Date().toISOString();
  pushSystemAlert(`Order ${order.code} delivered. Inventory updated automatically.`, "good");
  refreshAll();
}

function renderInvoices() {
  const wrap = qs("#invoiceTable");
  if (!db.invoices.length) {
    wrap.innerHTML = '<p class="subtle">No invoices yet.</p>';
    return;
  }

  wrap.innerHTML = `<table class="table">
    <thead>
      <tr>
        <th>Invoice</th>
        <th>Client</th>
        <th>Total</th>
        <th>Paid</th>
        <th>Balance</th>
        <th>Status</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      ${db.invoices
        .map((inv) => {
          const client = findById(db.clients, inv.clientId);
          const paid = invoicePaid(inv.id);
          const balance = inv.total - paid;
          const status = balance <= 0 ? "Paid" : "Unpaid";
          return `<tr>
            <td>${inv.code}</td>
            <td>${client ? client.name : "-"}</td>
            <td>${money(inv.total)}</td>
            <td>${money(paid)}</td>
            <td>${money(balance)}</td>
            <td>${statusBadge(status)}</td>
            <td><button type="button" class="ghost" data-inv-open="${inv.id}">Open</button></td>
          </tr>`;
        })
        .join("")}
    </tbody>
  </table>`;

  qsa("[data-inv-open]").forEach((btn) => {
    btn.addEventListener("click", () => openInvoiceDoc(btn.dataset.invOpen));
  });
}

function renderReceipts() {
  const wrap = qs("#receiptTable");
  if (!db.receipts.length) {
    wrap.innerHTML = '<p class="subtle">No receipts generated yet.</p>';
    return;
  }

  wrap.innerHTML = `<table class="table">
    <thead>
      <tr>
        <th>Receipt</th>
        <th>Invoice</th>
        <th>Amount</th>
        <th>Date</th>
        <th>Mode</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      ${db.receipts
        .map((r) => `<tr>
            <td>${r.code}</td>
            <td>${r.invoiceCode}</td>
            <td>${money(r.amount)}</td>
            <td>${day(r.createdAt)}</td>
            <td>${r.mode}</td>
            <td><button type="button" class="ghost" data-rec-open="${r.id}">Open</button></td>
          </tr>`)
        .join("")}
    </tbody>
  </table>`;

  qsa("[data-rec-open]").forEach((btn) => {
    btn.addEventListener("click", () => openReceiptDoc(btn.dataset.recOpen));
  });
}

function onPaymentSubmit(e) {
  e.preventDefault();
  const invoiceId = val("#paymentInvoice");
  const amount = num("#paymentAmount");
  const mode = val("#paymentMode");

  const invoice = findById(db.invoices, invoiceId);
  if (!invoice) return;
  if (amount > invoiceBalance(invoiceId)) {
    return alert("Amount exceeds invoice balance.");
  }

  createPayment(invoiceId, amount, mode);
  refreshAll();
}

function createPayment(invoiceId, amount, mode) {
  const invoice = findById(db.invoices, invoiceId);
  db.payments.push({
    id: uid("pay"),
    invoiceId,
    amount,
    mode,
    createdAt: new Date().toISOString()
  });

  const receipt = {
    id: uid("rcp"),
    code: `RCP-${Date.now().toString().slice(-6)}`,
    invoiceId,
    invoiceCode: invoice.code,
    amount,
    mode,
    createdAt: new Date().toISOString()
  };
  db.receipts.push(receipt);

  const order = db.orders.find((o) => o.id === invoice.orderId);
  if (order && invoiceBalance(invoiceId) <= 0) {
    order.paymentStatus = "Paid";
    pushSystemAlert(`Invoice ${invoice.code} fully paid. Order marked Paid.`, "good");
  } else if (order) {
    order.paymentStatus = "Partially Paid";
  }
}

function onExpenseSubmit(e) {
  e.preventDefault();
  db.expenses.push({
    id: uid("exp"),
    type: val("#expenseType"),
    supplierId: val("#expenseSupplier"),
    amount: num("#expenseAmount"),
    notes: val("#expenseNotes"),
    createdAt: new Date().toISOString()
  });
  e.target.reset();
  refreshAll();
}

function onMiningSubmit(e) {
  e.preventDefault();
  db.miningEntries.push({
    id: uid("mng"),
    date: val("#miningDate"),
    mineral: val("#miningMineral"),
    quantity: num("#miningQty"),
    hours: num("#miningHours"),
    productionLine: val("#miningLine"),
    staffCount: num("#miningStaff"),
    expatriates: num("#miningExpats"),
    laborCost: num("#miningLaborCost")
  });
  e.target.reset();
  refreshAll();
}

function onSettingsSubmit(e) {
  e.preventDefault();
  db.settings.businessName = val("#businessName");
  db.settings.businessAddress = val("#businessAddress");

  const logoFile = qs("#businessLogo").files[0];
  if (logoFile) {
    const reader = new FileReader();
    reader.onload = () => {
      db.settings.logoData = String(reader.result);
      refreshAll();
    };
    reader.readAsDataURL(logoFile);
  }

  refreshAll();
}

function renderSuppliers() {
  const wrap = qs("#supplierTable");
  if (!db.suppliers.length) {
    wrap.innerHTML = '<p class="subtle">No suppliers yet.</p>';
    return;
  }
  wrap.innerHTML = `<table class="table">
    <thead><tr><th>Name</th><th>Country</th><th>Contact</th><th>Terms</th><th>Balance Due</th></tr></thead>
    <tbody>
      ${db.suppliers
        .map((s) => {
          const due = supplierDue(s.id);
          return `<tr>
            <td>${s.name}</td>
            <td>${s.country}</td>
            <td>${s.contactPerson}</td>
            <td>${s.paymentTerms}</td>
            <td>${money(due)}</td>
          </tr>`;
        })
        .join("")}
    </tbody>
  </table>`;
}

function renderClients() {
  const wrap = qs("#clientTable");
  if (!db.clients.length) {
    wrap.innerHTML = '<p class="subtle">No clients yet.</p>';
    return;
  }

  wrap.innerHTML = `<table class="table">
    <thead><tr><th>Name</th><th>Phone</th><th>Email</th><th>Credit Limit</th><th>Outstanding</th><th>Alert</th></tr></thead>
    <tbody>
      ${db.clients
        .map((c) => {
          const outstanding = clientOutstanding(c.id);
          const exceeds = outstanding > c.creditLimit;
          return `<tr>
            <td>${c.name}</td>
            <td>${c.phone}</td>
            <td>${c.email}</td>
            <td>${money(c.creditLimit)}</td>
            <td>${money(outstanding)}</td>
            <td>${exceeds ? '<span class="badge bad">Over Limit</span>' : '<span class="badge good">OK</span>'}</td>
          </tr>`;
        })
        .join("")}
    </tbody>
  </table>`;
}

function renderInventory() {
  const wrap = qs("#inventoryTable");
  if (!db.items.length) {
    wrap.innerHTML = '<p class="subtle">No items yet.</p>';
    return;
  }

  wrap.innerHTML = `<table class="table">
    <thead>
      <tr>
        <th>SKU</th>
        <th>Part</th>
        <th>Category</th>
        <th>In Stock</th>
        <th>Reserved</th>
        <th>In Transit</th>
        <th>Available</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
      ${db.items
        .map((it) => {
          const transit = inTransitQty(it.id);
          const available = Math.max(0, it.stockOnHand - it.reserved);
          return `<tr>
            <td>${it.sku}</td>
            <td>${it.name}</td>
            <td>${it.category}</td>
            <td>${it.stockOnHand}</td>
            <td>${it.reserved}</td>
            <td>${transit}</td>
            <td>${available}</td>
            <td>${statusBadge(stockStatus(it))}</td>
          </tr>`;
        })
        .join("")}
    </tbody>
  </table>`;

  const valuation = db.items.reduce((acc, x) => acc + x.stockOnHand * x.unitCost, 0);
  qs("#inventoryValuation").textContent = `Auto stock valuation: ${money(valuation)}`;
}

function renderMining() {
  const wrap = qs("#miningTable");
  if (!db.miningEntries.length) {
    wrap.innerHTML = '<p class="subtle">No production entries yet.</p>';
    return;
  }

  const monthly = groupByMonth(db.miningEntries);

  wrap.innerHTML = `<table class="table">
    <thead>
      <tr>
        <th>Month</th>
        <th>Total Output</th>
        <th>Total Hours</th>
        <th>Labor Cost</th>
        <th>Output / Hour</th>
        <th>Cost / Output</th>
      </tr>
    </thead>
    <tbody>
      ${Object.entries(monthly)
        .map(([month, rows]) => {
          const totalQty = sum(rows, "quantity");
          const totalHours = sum(rows, "hours");
          const totalCost = sum(rows, "laborCost");
          const eff = totalHours > 0 ? totalQty / totalHours : 0;
          const cpu = totalQty > 0 ? totalCost / totalQty : 0;
          return `<tr>
            <td>${month}</td>
            <td>${totalQty.toFixed(2)}</td>
            <td>${totalHours.toFixed(2)}</td>
            <td>${money(totalCost)}</td>
            <td>${eff.toFixed(2)}</td>
            <td>${money(cpu)}</td>
          </tr>`;
        })
        .join("")}
    </tbody>
  </table>`;
}

function renderDashboard() {
  const kpis = qs("#kpis");
  const totalRevenue = db.payments.reduce((acc, x) => acc + x.amount, 0);
  const totalInvoiced = db.invoices.reduce((acc, x) => acc + x.total, 0);
  const totalOutstanding = totalInvoiced - totalRevenue;
  const totalExpenses = db.expenses.reduce((acc, x) => acc + x.amount, 0);
  const supplierDues = totalSupplierDue();
  const monthSales = thisMonthSales();

  kpis.innerHTML = [
    ["Revenue (Collected)", money(totalRevenue)],
    ["Outstanding (A/R)", money(totalOutstanding)],
    ["Supplier Dues (A/P)", money(supplierDues)],
    ["Monthly Sales", money(monthSales)],
    ["Expenses", money(totalExpenses)],
    ["Orders", String(db.orders.length)],
    ["POs In Transit", String(db.purchaseOrders.filter((x) => x.status === "In Transit").length)],
    ["Mining Output (Month)", String(thisMonthMiningOutput().toFixed(2))]
  ]
    .map(([t, v]) => `<div class="kpi"><h4>${t}</h4><p>${v}</p></div>`)
    .join("");

  renderAlerts();
  renderFastMoving();
  renderOutOfStock();
  renderTopCustomers();
  renderMiningTrend();
}

function renderAlerts() {
  const alerts = [];

  db.items.forEach((item) => {
    if (availableStock(item.id) <= item.reorderLevel) {
      alerts.push({
        type: "warn",
        text: `Low stock alert: ${item.sku} (${availableStock(item.id)} available). Re-order recommended.`
      });
    }
  });

  db.invoices.forEach((inv) => {
    const bal = invoiceBalance(inv.id);
    if (bal > 0) {
      alerts.push({
        type: "bad",
        text: `Unpaid invoice: ${inv.code} has outstanding ${money(bal)}.`
      });
    }
  });

  db.clients.forEach((client) => {
    const out = clientOutstanding(client.id);
    if (out > client.creditLimit) {
      alerts.push({
        type: "bad",
        text: `Credit limit exceeded: ${client.name}. Outstanding ${money(out)}.`
      });
    }
  });

  const due = totalSupplierDue();
  if (due > 0) {
    alerts.push({
      type: "warn",
      text: `Supplier dues pending: ${money(due)}.`
    });
  }

  const cache = readAlertCache();
  alerts.push(...cache);

  const wrap = qs("#alerts");
  if (!alerts.length) {
    wrap.innerHTML = '<div class="alert good">All critical indicators are healthy.</div>';
    return;
  }

  wrap.innerHTML = alerts
    .slice(0, 12)
    .map((a) => `<div class="alert ${a.type}">${a.text}</div>`)
    .join("");
}

function renderFastMoving() {
  const rows = [...db.items]
    .sort((a, b) => b.sold - a.sold)
    .slice(0, 5)
    .map((x) => `<div class="row"><span>${x.sku} - ${x.name}</span><span>${x.sold} sold</span></div>`)
    .join("");
  qs("#fastMoving").innerHTML = rows || '<p class="subtle">No sales history yet.</p>';
}

function renderOutOfStock() {
  const rows = db.items
    .filter((x) => availableStock(x.id) <= 0)
    .map((x) => `<div class="row"><span>${x.sku} - ${x.name}</span><span class="badge bad">Out of Stock</span></div>`)
    .join("");
  qs("#outOfStock").innerHTML = rows || '<p class="subtle">No out-of-stock items currently.</p>';
}

function renderTopCustomers() {
  const totals = db.clients.map((c) => {
    const clientInvoices = db.invoices.filter((i) => i.clientId === c.id);
    const amount = clientInvoices.reduce((acc, x) => acc + x.total, 0);
    return { name: c.name, amount };
  });
  const rows = totals
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 5)
    .map((x) => `<div class="row"><span>${x.name}</span><span>${money(x.amount)}</span></div>`)
    .join("");
  qs("#topCustomers").innerHTML = rows || '<p class="subtle">No customer data yet.</p>';
}

function renderMiningTrend() {
  const monthly = groupByMonth(db.miningEntries);
  const rows = Object.entries(monthly)
    .map(([m, list]) => {
      const qty = sum(list, "quantity");
      const hrs = sum(list, "hours");
      const cost = sum(list, "laborCost");
      return `<div class="row"><span>${m}</span><span>Qty ${qty.toFixed(2)} | Hrs ${hrs.toFixed(2)} | Cost ${money(cost)}</span></div>`;
    })
    .join("");
  qs("#miningTrend").innerHTML = rows || '<p class="subtle">No mining entries yet.</p>';
}

function renderHeaderSettings() {
  qs("#headerBusinessName").textContent = db.settings.businessName || "GMI TERRALINK";
  const logo = qs("#headerLogo");
  if (db.settings.logoData) {
    logo.src = db.settings.logoData;
    logo.classList.remove("hidden");
  } else {
    logo.classList.add("hidden");
  }

  qs("#businessName").value = db.settings.businessName;
  qs("#businessAddress").value = db.settings.businessAddress;
}

function renderSettingsPreview() {
  const preview = qs("#documentPreview");
  preview.innerHTML = "";

  const invHtml = buildDocMarkup(
    "Invoice Preview",
    `<p>Business details and logo will appear here.</p>
     <p><strong>Business Name:</strong> ${escapeHtml(db.settings.businessName)}</p>
     <p><strong>Address:</strong> ${escapeHtml(db.settings.businessAddress)}</p>`
  );

  preview.innerHTML = invHtml;
}

function openInvoiceDoc(invoiceId) {
  const invoice = findById(db.invoices, invoiceId);
  if (!invoice) return;
  const order = db.orders.find((o) => o.id === invoice.orderId);
  const client = findById(db.clients, invoice.clientId);
  const paid = invoicePaid(invoice.id);
  const balance = invoice.total - paid;

  const lines = (order ? order.lines : [])
    .map((line) => {
      const item = findById(db.items, line.itemId);
      const part = item ? `${item.sku} - ${item.name}` : line.itemId;
      return `<tr><td>${part}</td><td>${line.qty}</td><td>${money(line.unitPrice)}</td><td>${money(line.qty * line.unitPrice)}</td></tr>`;
    })
    .join("");

  const body = `
    <p><strong>Invoice No:</strong> ${invoice.code}</p>
    <p><strong>Date:</strong> ${day(invoice.issuedAt)}</p>
    <p><strong>Client:</strong> ${client ? client.name : "-"}</p>
    <table style="width:100%; border-collapse:collapse; margin-top:8px;">
      <thead><tr><th style="text-align:left; border-bottom:1px solid #ddd;">Item</th><th style="text-align:left; border-bottom:1px solid #ddd;">Qty</th><th style="text-align:left; border-bottom:1px solid #ddd;">Price</th><th style="text-align:left; border-bottom:1px solid #ddd;">Total</th></tr></thead>
      <tbody>${lines}</tbody>
    </table>
    <p><strong>Total:</strong> ${money(invoice.total)}</p>
    <p><strong>Paid:</strong> ${money(paid)}</p>
    <p><strong>Balance:</strong> ${money(balance)}</p>
  `;

  openDocWindow("Invoice", body);
}

function openReceiptDoc(receiptId) {
  const receipt = findById(db.receipts, receiptId);
  if (!receipt) return;

  const invoice = findById(db.invoices, receipt.invoiceId);
  const client = invoice ? findById(db.clients, invoice.clientId) : null;

  const body = `
    <p><strong>Receipt No:</strong> ${receipt.code}</p>
    <p><strong>Date:</strong> ${day(receipt.createdAt)}</p>
    <p><strong>Received From:</strong> ${client ? client.name : "-"}</p>
    <p><strong>Invoice:</strong> ${receipt.invoiceCode}</p>
    <p><strong>Amount:</strong> ${money(receipt.amount)}</p>
    <p><strong>Mode:</strong> ${receipt.mode}</p>
  `;

  openDocWindow("Receipt", body);
}

function openDocWindow(title, bodyHtml) {
  const win = window.open("", "_blank", "width=900,height=700");
  if (!win) return;
  const html = `<!doctype html>
<html>
<head>
  <title>${escapeHtml(title)}</title>
  <style>
    body { font-family: Arial, sans-serif; color: #111; margin: 20px; }
    .doc-head { display:flex; gap: 12px; border-bottom:1px solid #ddd; padding-bottom:10px; margin-bottom:10px; }
    .logo { width: 64px; height: 64px; object-fit: cover; border:1px solid #ddd; border-radius:8px; }
  </style>
</head>
<body>
  <div class="doc-head">
    ${db.settings.logoData ? `<img class="logo" src="${db.settings.logoData}" alt="logo" />` : ""}
    <div>
      <h2 style="margin:0;">${escapeHtml(title)}</h2>
      <h3 style="margin:0;">${escapeHtml(db.settings.businessName)}</h3>
      <p style="margin:4px 0 0;">${escapeHtml(db.settings.businessAddress)}</p>
    </div>
  </div>
  ${bodyHtml}
  <script>window.print();</script>
</body>
</html>`;
  win.document.write(html);
  win.document.close();
}

function buildDocMarkup(title, bodyHtml) {
  return `<div class="doc-wrap">
    <div class="doc-head">
      ${db.settings.logoData ? `<img class="doc-logo" src="${db.settings.logoData}" alt="Logo" />` : ""}
      <div>
        <h2 class="doc-title">${escapeHtml(title)}</h2>
        <h3 class="doc-business">${escapeHtml(db.settings.businessName)}</h3>
        <p class="doc-address">${escapeHtml(db.settings.businessAddress)}</p>
      </div>
    </div>
    <div class="doc-body">${bodyHtml}</div>
  </div>`;
}

function canFulfill(lines) {
  return lines.every((line) => availableStock(line.itemId) >= line.qty);
}

function reserveOrderLines(lines) {
  lines.forEach((line) => {
    const item = findById(db.items, line.itemId);
    if (!item) return;
    item.reserved += line.qty;
  });
}

function inTransitQty(itemId) {
  return db.purchaseOrders
    .filter((po) => po.status === "Shipped" || po.status === "In Transit")
    .reduce((acc, po) => {
      const line = po.lines.find((l) => l.itemId === itemId);
      return acc + (line ? line.qty : 0);
    }, 0);
}

function availableStock(itemId) {
  const item = findById(db.items, itemId);
  if (!item) return 0;
  return Math.max(0, item.stockOnHand - item.reserved);
}

function stockStatus(item) {
  const available = availableStock(item.id);
  if (available <= 0) return "Out of Stock";
  if (available <= item.reorderLevel) return "Low Stock";
  return "In Stock";
}

function statusBadge(label) {
  const norm = String(label).toLowerCase();
  const cls =
    norm.includes("out") || norm.includes("unpaid") || norm.includes("awaiting")
      ? "bad"
      : norm.includes("low") || norm.includes("partial") || norm.includes("transit")
      ? "warn"
      : "good";
  return `<span class="badge ${cls}">${escapeHtml(label)}</span>`;
}

function supplierDue(supplierId) {
  const poTotal = db.purchaseOrders
    .filter((po) => po.supplierId === supplierId)
    .reduce((acc, po) => acc + po.lines.reduce((x, l) => x + l.qty * l.unitPrice, 0), 0);

  const expensePaid = db.expenses
    .filter((e) => e.supplierId === supplierId && (e.type === "Supplier Invoice" || e.type === "Logistics"))
    .reduce((acc, e) => acc + e.amount, 0);

  return Math.max(0, poTotal - expensePaid);
}

function totalSupplierDue() {
  return db.suppliers.reduce((acc, s) => acc + supplierDue(s.id), 0);
}

function invoicePaid(invoiceId) {
  return db.payments.filter((p) => p.invoiceId === invoiceId).reduce((acc, p) => acc + p.amount, 0);
}

function invoiceBalance(invoiceId) {
  const inv = findById(db.invoices, invoiceId);
  if (!inv) return 0;
  return Math.max(0, inv.total - invoicePaid(invoiceId));
}

function clientOutstanding(clientId) {
  return db.invoices
    .filter((x) => x.clientId === clientId)
    .reduce((acc, x) => acc + invoiceBalance(x.id), 0);
}

function thisMonthSales() {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();
  return db.payments
    .filter((p) => {
      const d = new Date(p.createdAt);
      return d.getFullYear() === y && d.getMonth() === m;
    })
    .reduce((acc, p) => acc + p.amount, 0);
}

function thisMonthMiningOutput() {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();
  return db.miningEntries
    .filter((x) => {
      const d = new Date(x.date);
      return d.getFullYear() === y && d.getMonth() === m;
    })
    .reduce((acc, x) => acc + x.quantity, 0);
}

function groupByMonth(rows) {
  return rows.reduce((acc, row) => {
    const d = new Date(row.date || row.createdAt);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    (acc[key] ||= []).push(row);
    return acc;
  }, {});
}

function sum(rows, field) {
  return rows.reduce((acc, x) => acc + Number(x[field] || 0), 0);
}

function pushSystemAlert(text, type) {
  const cache = readAlertCache();
  cache.unshift({ text, type });
  localStorage.setItem("gmi_alert_cache", JSON.stringify(cache.slice(0, 8)));
}

function readAlertCache() {
  try {
    return JSON.parse(localStorage.getItem("gmi_alert_cache") || "[]");
  } catch (_err) {
    return [];
  }
}

function findById(arr, id) {
  return arr.find((x) => x.id === id);
}

function qs(sel) {
  return document.querySelector(sel);
}

function qsa(sel) {
  return [...document.querySelectorAll(sel)];
}

function val(sel) {
  return qs(sel).value;
}

function num(sel) {
  return Number(qs(sel).value || 0);
}

function escapeHtml(str) {
  return String(str || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
