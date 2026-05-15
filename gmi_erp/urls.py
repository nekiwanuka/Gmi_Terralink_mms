from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views import (
    ClientViewSet,
    ExpenseViewSet,
    InventoryItemViewSet,
    MiningEntryViewSet,
    PayrollEntryViewSet,
    PaymentViewSet,
    PurchaseOrderViewSet,
    ReceiptViewSet,
    SalesOrderViewSet,
    SupplierViewSet,
    access_denied,
    billing_expenses,
    billing_overview,
    billing_pay_invoice,
    contacts_clients,
    contacts_edit_client,
    contacts_edit_supplier,
    contacts_suppliers,
    dashboard,
    inventory_create,
    inventory_edit,
    inventory_list,
    invoice_document,
    locations_list,
    login_view,
    logout_view,
    mining_create,
    mining_list,
    notice_board,
    notice_task_done,
    payroll_create,
    payroll_list,
    procurement_create,
    procurement_list,
    procurement_update_status,
    quotation_convert,
    quotation_create,
    quotation_detail,
    quotation_document,
    quotation_list,
    quotation_set_status,
    receipt_document,
    reports_overview,
    sales_create,
    sales_deliver,
    sales_detail,
    sales_list,
    sales_pay_invoice,
    settings_page,
    stock_adjust,
    stock_movements,
    stock_request_cancel,
    stock_request_create,
    stock_request_decide,
    stock_request_fulfill,
    stock_request_list,
    stock_transfer,
    switch_currency,
    warehouse_receive,
)

router = DefaultRouter()
router.register("suppliers", SupplierViewSet)
router.register("clients", ClientViewSet)
router.register("items", InventoryItemViewSet)
router.register("purchase-orders", PurchaseOrderViewSet)
router.register("sales-orders", SalesOrderViewSet)
router.register("payments", PaymentViewSet)
router.register("receipts", ReceiptViewSet)
router.register("expenses", ExpenseViewSet)
router.register("mining-entries", MiningEntryViewSet)
router.register("payroll-entries", PayrollEntryViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/", include(router.urls)),
    # Auth
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("access-denied/", access_denied, name="access_denied"),
    # Dashboard & settings
    path("", dashboard, name="dashboard"),
    path("settings/", settings_page, name="settings"),
    path("settings/currency/", switch_currency, name="switch_currency"),
    # Notice board
    path("notice-board/", notice_board, name="notice_board"),
    path("notice-board/<int:pk>/done/", notice_task_done, name="notice_task_done"),
    # Procurement
    path("procurement/", procurement_list, name="procurement_list"),
    path("procurement/new/", procurement_create, name="procurement_create"),
    path(
        "procurement/<int:pk>/status/",
        procurement_update_status,
        name="procurement_update_status",
    ),
    path("procurement/<int:pk>/receive/", warehouse_receive, name="warehouse_receive"),
    # Inventory
    path("inventory/", inventory_list, name="inventory_list"),
    path("inventory/new/", inventory_create, name="inventory_create"),
    path("inventory/<int:pk>/edit/", inventory_edit, name="inventory_edit"),
    path("inventory/locations/", locations_list, name="locations_list"),
    path("inventory/transfer/", stock_transfer, name="stock_transfer"),
    path("inventory/adjust/", stock_adjust, name="stock_adjust"),
    path("inventory/movements/", stock_movements, name="stock_movements"),
    path("inventory/requests/", stock_request_list, name="stock_request_list"),
    path("inventory/requests/new/", stock_request_create, name="stock_request_create"),
    path(
        "inventory/requests/<int:pk>/decide/",
        stock_request_decide,
        name="stock_request_decide",
    ),
    path(
        "inventory/requests/<int:pk>/fulfill/",
        stock_request_fulfill,
        name="stock_request_fulfill",
    ),
    path(
        "inventory/requests/<int:pk>/cancel/",
        stock_request_cancel,
        name="stock_request_cancel",
    ),
    # Sales
    path("sales/", sales_list, name="sales_list"),
    path("sales/new/", sales_create, name="sales_create"),
    path("sales/<int:pk>/", sales_detail, name="sales_detail"),
    path("sales/<int:pk>/deliver/", sales_deliver, name="sales_deliver"),
    path("sales/pay/<int:pk>/", sales_pay_invoice, name="sales_pay_invoice"),
    # Quotations
    path("quotations/", quotation_list, name="quotation_list"),
    path("quotations/new/", quotation_create, name="quotation_create"),
    path("quotations/<int:pk>/", quotation_detail, name="quotation_detail"),
    path(
        "quotations/<int:pk>/status/",
        quotation_set_status,
        name="quotation_set_status",
    ),
    path("quotations/<int:pk>/convert/", quotation_convert, name="quotation_convert"),
    # Billing
    path("billing/", billing_overview, name="billing_overview"),
    path("billing/pay/<int:pk>/", billing_pay_invoice, name="billing_pay_invoice"),
    path("billing/expenses/", billing_expenses, name="billing_expenses"),
    # Contacts
    path("contacts/suppliers/", contacts_suppliers, name="contacts_suppliers"),
    path(
        "contacts/suppliers/<int:pk>/edit/",
        contacts_edit_supplier,
        name="contacts_edit_supplier",
    ),
    path("contacts/clients/", contacts_clients, name="contacts_clients"),
    path(
        "contacts/clients/<int:pk>/edit/",
        contacts_edit_client,
        name="contacts_edit_client",
    ),
    # Mining
    path("mining/", mining_list, name="mining_list"),
    path("mining/new/", mining_create, name="mining_create"),
    # Payroll
    path("payroll/", payroll_list, name="payroll_list"),
    path("payroll/new/", payroll_create, name="payroll_create"),
    # Reports
    path("reports/", reports_overview, name="reports_overview"),
    # Documents
    path(
        "documents/invoice/<int:invoice_id>/", invoice_document, name="invoice_document"
    ),
    path(
        "documents/receipt/<int:receipt_id>/", receipt_document, name="receipt_document"
    ),
    path(
        "documents/quotation/<int:pk>/", quotation_document, name="quotation_document"
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
