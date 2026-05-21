from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .decorators import role_required
from .forms import (
    ClientForm,
    ExpenseForm,
    InventoryItemForm,
    MiningEntryForm,
    NoticeTaskForm,
    PayrollEntryForm,
    PurchaseOrderForm,
    PurchaseOrderStatusForm,
    QuotationForm,
    SupplierForm,
)
from .models import (
    ActionRequest,
    BusinessProfile,
    Brand,
    Category,
    Client,
    Expense,
    InventoryItem,
    Invoice,
    Location,
    MiningEntry,
    NoticeTask,
    PayrollEntry,
    Payment,
    PurchaseOrder,
    PurchaseOrderLine,
    Quotation,
    QuotationLine,
    Receipt,
    SalesOrder,
    SalesOrderLine,
    StockLocation,
    StockMovement,
    Supplier,
    UserProfile,
    convert_quotation_to_sales_order,
    create_payment_and_receipt,
    create_sales_order_with_invoice,
    deliver_sales_order,
    fulfill_stock_request,
    generate_code,
    get_main_store,
    get_main_warehouse,
    get_stock_quantity,
    receive_purchase_order,
    record_stock_movement,
    split_purchase_order_line,
    update_purchase_order_split_quantity,
)
from .models import StockRequest
from .serializers import (
    ClientSerializer,
    ExpenseSerializer,
    InventoryItemSerializer,
    MiningEntrySerializer,
    PayrollEntrySerializer,
    PaymentCreateWithReceiptSerializer,
    PaymentSerializer,
    PurchaseOrderReceiveSerializer,
    PurchaseOrderSerializer,
    ReceiptSerializer,
    SalesOrderSerializer,
    SupplierSerializer,
)

# ---------- DRF ViewSets (API kept intact) ----------


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by("-id")
    serializer_class = SupplierSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by("-id")
    serializer_class = ClientSerializer


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all().order_by("-id")
    serializer_class = InventoryItemSerializer


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.prefetch_related("lines").order_by("-id")
    serializer_class = PurchaseOrderSerializer

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        po = self.get_object()
        serializer = PurchaseOrderReceiveSerializer(
            data=request.data, context={"po": po}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Receiving applied and inventory updated."})


class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.prefetch_related("lines").order_by("-id")
    serializer_class = SalesOrderSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["deposit"] = self.request.data.get("deposit", "0")
        return ctx

    @action(detail=True, methods=["post"])
    def deliver(self, request, pk=None):
        order = self.get_object()
        deliver_sales_order(order)
        return Response({"detail": "Order delivered and inventory reduced."})


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("invoice").order_by("-id")
    serializer_class = PaymentSerializer

    @action(detail=False, methods=["post"])
    def with_receipt(self, request):
        serializer = PaymentCreateWithReceiptSerializer(
            data=request.data,
            context={"invoice_model": Invoice},
        )
        serializer.is_valid(raise_exception=True)
        receipt = serializer.save()
        return Response(
            {"receipt_id": receipt.id, "receipt_code": receipt.code},
            status=status.HTTP_201_CREATED,
        )


class ReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Receipt.objects.select_related("payment", "payment__invoice").order_by(
        "-id"
    )
    serializer_class = ReceiptSerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.select_related("supplier").order_by("-id")
    serializer_class = ExpenseSerializer


class MiningEntryViewSet(viewsets.ModelViewSet):
    queryset = MiningEntry.objects.all().order_by("-date", "-id")
    serializer_class = MiningEntrySerializer


class PayrollEntryViewSet(viewsets.ModelViewSet):
    queryset = PayrollEntry.objects.all().order_by("-date", "-id")
    serializer_class = PayrollEntrySerializer


# ---------- Internal helpers ----------


def _get_profile():
    profile, _ = BusinessProfile.objects.get_or_create(id=1)
    return profile


# Backward-compat alias used by older code paths
get_profile = _get_profile


def _current_user_role(request):
    if not request.user.is_authenticated:
        return None
    if request.user.is_superuser:
        return UserProfile.ROLE_OWNER
    try:
        return request.user.profile.role
    except AttributeError:
        return None


def _effective_notice_roles(user_role):
    effective_roles = {user_role} if user_role else set()
    if user_role == UserProfile.ROLE_WAREHOUSE_MANAGER:
        effective_roles.add(UserProfile.ROLE_WAREHOUSE)
    if user_role == UserProfile.ROLE_SALES_ATTENDANT:
        effective_roles.add(UserProfile.ROLE_SALES)
    if user_role == UserProfile.ROLE_STORE_MANAGER:
        effective_roles.update({UserProfile.ROLE_SALES, UserProfile.ROLE_OPERATIONS})
    return effective_roles


def _can_complete_notice_task(request, task):
    if task.is_done:
        return False
    user_role = _current_user_role(request)
    if request.user.is_superuser or user_role in (
        UserProfile.ROLE_OWNER,
        UserProfile.ROLE_ADMIN,
        UserProfile.ROLE_GENERAL_MANAGER,
    ):
        return True
    return task.target_role in _effective_notice_roles(user_role)


def _build_alerts():
    alerts = []
    currency_code = _get_profile().currency_code
    warehouse = get_main_warehouse()
    store = get_main_store()
    for item in InventoryItem.objects.all():
        warehouse_qty = get_stock_quantity(item, warehouse)
        store_qty = get_stock_quantity(item, store)
        if warehouse_qty <= item.reorder_level:
            alerts.append(
                f"Warehouse low stock: {item.sku} — {warehouse_qty} available."
            )
        if store_qty <= item.reorder_level:
            alerts.append(f"Storefront low stock: {item.sku} — {store_qty} available.")
        if item.status in (InventoryItem.STATUS_DAMAGED, InventoryItem.STATUS_EXPIRED):
            alerts.append(
                f"Attention needed: {item.sku} is marked {item.status.lower()}."
            )
    for inv in Invoice.objects.filter(balance__gt=0):
        alerts.append(
            f"Unpaid invoice {inv.code}: balance {currency_code} {inv.balance:,}."
        )
    for client in Client.objects.all():
        outstanding = sum(inv.balance for inv in client.invoices.all())
        if outstanding > client.credit_limit > 0:
            alerts.append(f"Credit limit exceeded: {client.name}.")
    if not alerts:
        alerts.append("All critical indicators are currently healthy.")
    return alerts[:12]


build_alerts = _build_alerts


def _parse_lines(post_data):
    lines = []
    i = 0
    while True:
        item_id = post_data.get(f"line_{i}_item")
        qty = post_data.get(f"line_{i}_qty")
        price = post_data.get(f"line_{i}_price")
        if item_id is None:
            break
        if item_id and qty and price:
            try:
                lines.append(
                    {
                        "item_id": int(item_id),
                        "quantity": int(qty),
                        "unit_price": Decimal(price),
                    }
                )
            except (ValueError, Exception):
                pass
        i += 1
    return lines


# ---------- Authentication ----------


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get("next", "dashboard"))
    return render(request, "auth/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


def access_denied(request):
    return render(request, "auth/access_denied.html")


# ---------- Dashboard ----------


@role_required("Owner", "Procurement", "Finance", "Warehouse", "Sales", "Operations")
def dashboard(request):
    total_invoiced = Invoice.objects.aggregate(x=Sum("total_amount")).get("x") or 0
    total_paid = Payment.objects.aggregate(x=Sum("amount")).get("x") or 0
    outstanding = total_invoiced - total_paid
    expenses_total = Expense.objects.aggregate(x=Sum("amount")).get("x") or 0

    supplier_dues = 0
    for s in Supplier.objects.prefetch_related("purchase_orders", "expenses"):
        po_total = sum(po.total_amount for po in s.purchase_orders.all())
        spent = s.expenses.aggregate(x=Sum("amount")).get("x") or 0
        supplier_dues += max(0, po_total - spent)

    items = InventoryItem.objects.all()
    warehouse = get_main_warehouse()
    store = get_main_store()
    out_of_stock = items.filter(stock_on_hand__lte=F("reserved_stock")).count()
    low_stock = [i for i in items if 0 < i.available_stock <= i.reorder_level]
    warehouse_stock = (
        StockLocation.objects.filter(location=warehouse)
        .aggregate(x=Sum("quantity"))
        .get("x")
        or 0
    )
    storefront_stock = (
        StockLocation.objects.filter(location=store)
        .aggregate(x=Sum("quantity"))
        .get("x")
        or 0
    )

    now = timezone.localdate()
    month_sales = (
        Payment.objects.filter(created_at__year=now.year, created_at__month=now.month)
        .aggregate(x=Sum("amount"))
        .get("x")
        or 0
    )
    today_sales = (
        Payment.objects.filter(created_at__date=now, is_refunded=False)
        .aggregate(x=Sum("amount"))
        .get("x")
        or 0
    )
    top_products = (
        SalesOrderLine.objects.filter(sales_order__actual_delivery_date__isnull=False)
        .values("item__sku", "item__name")
        .annotate(qty=Sum("quantity"), revenue=Sum(F("quantity") * F("unit_price")))
        .order_by("-qty")[:5]
    )
    month_output = (
        MiningEntry.objects.filter(date__year=now.year, date__month=now.month)
        .aggregate(x=Sum("quantity_produced"))
        .get("x")
        or 0
    )
    top_customers = (
        Invoice.objects.values("client__name")
        .annotate(total=Sum("total_amount"))
        .order_by("-total")[:5]
    )
    return render(
        request,
        "dashboard.html",
        {
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "outstanding": outstanding,
            "expenses": expenses_total,
            "supplier_dues": supplier_dues,
            "low_stock_count": len(low_stock),
            "out_of_stock_count": out_of_stock,
            "month_sales": month_sales,
            "today_sales": today_sales,
            "month_output": month_output,
            "warehouse_stock": warehouse_stock,
            "storefront_stock": storefront_stock,
            "pending_requests": StockRequest.objects.filter(
                status=StockRequest.STATUS_PENDING
            ).count(),
            "top_products": top_products,
            "top_customers": top_customers,
            "recent_orders": SalesOrder.objects.select_related("client").order_by(
                "-id"
            )[:10],
            "recent_pos": PurchaseOrder.objects.select_related("supplier").order_by(
                "-id"
            )[:10],
            "alerts": _build_alerts(),
        },
    )


# ---------- Settings ----------


@role_required("Owner")
def switch_currency(request):
    if request.method == "POST":
        profile = _get_profile()
        currency_code = request.POST.get("currency_code", profile.currency_code)
        if currency_code in dict(BusinessProfile.CURRENCY_CHOICES):
            profile.currency_code = currency_code
            profile.save(update_fields=["currency_code"])
            messages.success(request, f"Currency switched to {currency_code}.")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    if not next_url.startswith("/"):
        next_url = "/"
    return redirect(next_url)


@role_required("Owner")
def settings_page(request):
    profile = _get_profile()
    users = UserProfile.objects.select_related("user").order_by("user__username")
    if request.method == "POST":
        act = request.POST.get("action")
        if act == "profile":
            profile.business_name = request.POST.get(
                "business_name", profile.business_name
            )
            profile.business_address = request.POST.get(
                "business_address", profile.business_address
            )
            profile.business_phone = request.POST.get(
                "business_phone", profile.business_phone
            )
            profile.business_email = request.POST.get(
                "business_email", profile.business_email
            )
            profile.business_website = request.POST.get(
                "business_website", profile.business_website
            )
            currency_code = request.POST.get("currency_code", profile.currency_code)
            if currency_code in dict(BusinessProfile.CURRENCY_CHOICES):
                profile.currency_code = currency_code
            if request.FILES.get("logo"):
                profile.logo = request.FILES["logo"]
            profile.save()
            messages.success(request, "Business profile updated.")
        elif act == "role":
            uid = request.POST.get("user_id")
            new_role = request.POST.get("role")
            if uid and new_role and new_role in dict(UserProfile.ROLE_CHOICES):
                up = get_object_or_404(UserProfile, pk=uid)
                up.role = new_role
                up.save()
                messages.success(
                    request, f"Role for {up.user.username} set to {new_role}."
                )
        return redirect("settings")
    return render(
        request,
        "settings.html",
        {
            "profile": profile,
            "currency_choices": BusinessProfile.CURRENCY_CHOICES,
            "users": users,
            "role_choices": UserProfile.ROLE_CHOICES,
        },
    )


# ---------- Notice Board ----------


@role_required(
    "Owner",
    "Admin",
    "General Manager",
    "Procurement",
    "Finance",
    "Warehouse",
    "Warehouse Manager",
    "Sales",
    "Sales Attendant",
    "Store Manager",
    "Operations",
)
def notice_board(request):
    form = NoticeTaskForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.created_by = request.user
        task.save()
        messages.success(request, f"Task sent to {task.target_role}.")
        return redirect("notice_board")

    tasks = list(
        NoticeTask.objects.select_related("created_by", "completed_by").order_by(
            "completed_at", "-created_at"
        )[:200]
    )
    for task in tasks:
        task.can_mark_done = _can_complete_notice_task(request, task)
    user_role = _current_user_role(request)
    my_open_count = sum(
        1
        for task in tasks
        if not task.is_done and task.target_role in _effective_notice_roles(user_role)
    )
    return render(
        request,
        "notice_board.html",
        {"form": form, "tasks": tasks, "my_open_count": my_open_count},
    )


@role_required(
    "Owner",
    "Admin",
    "General Manager",
    "Procurement",
    "Finance",
    "Warehouse",
    "Warehouse Manager",
    "Sales",
    "Sales Attendant",
    "Store Manager",
    "Operations",
)
def notice_task_done(request, pk):
    task = get_object_or_404(NoticeTask, pk=pk)
    if request.method == "POST":
        if _can_complete_notice_task(request, task):
            task.mark_done(request.user)
            messages.success(request, f"Task '{task.title}' marked done.")
        else:
            messages.error(request, "Only the receiving team can mark this task done.")
    return redirect("notice_board")


# ---------- Procurement ----------


@role_required("Owner", "Procurement", "Warehouse", "Finance")
def procurement_list(request):
    status_filter = request.GET.get("status", "")
    pos = (
        PurchaseOrder.objects.select_related("supplier", "parent_order")
        .prefetch_related("lines__item")
        .order_by("-id")
    )
    if status_filter:
        pos = pos.filter(status=status_filter)
    return render(
        request,
        "procurement/list.html",
        {
            "pos": pos,
            "suppliers": Supplier.objects.order_by("name"),
            "status_choices": PurchaseOrder.STATUS_CHOICES,
            "current_status": status_filter,
        },
    )


@role_required("Owner", "Procurement", "Warehouse")
def procurement_create(request):
    items = InventoryItem.objects.all().order_by("name")
    form = PurchaseOrderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lines = _parse_lines(request.POST)
        if not lines:
            messages.error(request, "Add at least one item line.")
        else:
            with transaction.atomic():
                po = form.save(commit=False)
                po.code = generate_code("PO")
                po.save()
                for ln in lines:
                    PurchaseOrderLine.objects.create(
                        purchase_order=po,
                        item_id=ln["item_id"],
                        quantity=ln["quantity"],
                        unit_price=ln["unit_price"],
                    )
            messages.success(request, f"Purchase order {po.code} created.")
            return redirect("procurement_list")
    return render(request, "procurement/create.html", {"form": form, "items": items})


@role_required("Owner", "Procurement", "Warehouse")
def procurement_update_status(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == "POST":
        form = PurchaseOrderStatusForm(request.POST, instance=po)
        if form.is_valid():
            form.save()
            messages.success(request, f"{po.code} updated.")
    return redirect("procurement_list")


@role_required("Owner", "Procurement", "Warehouse")
def procurement_split_line(request, pk):
    line = get_object_or_404(
        PurchaseOrderLine.objects.select_related("purchase_order", "item"), pk=pk
    )
    if request.method == "POST":
        try:
            supplier = Supplier.objects.get(pk=request.POST.get("supplier"))
            split_po = split_purchase_order_line(
                parent_line=line,
                supplier=supplier,
                quantity=request.POST.get("quantity", 0),
            )
            messages.success(
                request,
                f"Created split PO {split_po.code}; main PO balance was updated.",
            )
        except Supplier.DoesNotExist:
            messages.error(request, "Choose a supplier for the split quantity.")
        except (ValidationError, ValueError) as e:
            messages.error(request, str(e))
    return redirect("procurement_list")


@role_required("Owner", "Procurement", "Warehouse")
def procurement_update_split_quantity(request, pk):
    split_po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == "POST":
        try:
            update_purchase_order_split_quantity(
                split_po=split_po,
                quantity=request.POST.get("quantity", 0),
            )
            messages.success(request, f"Split quantity for {split_po.code} updated.")
        except (
            PurchaseOrderLine.DoesNotExist,
            PurchaseOrderLine.MultipleObjectsReturned,
            ValidationError,
            ValueError,
        ) as e:
            messages.error(request, str(e))
    return redirect("procurement_list")


@role_required("Owner", "Procurement", "Warehouse")
def warehouse_receive(request, pk):
    po = get_object_or_404(PurchaseOrder.objects.prefetch_related("lines__item"), pk=pk)
    if request.method == "POST":
        line_updates = [
            {
                "line": line,
                "received_quantity": request.POST.get(f"received_{line.pk}", 0),
                "damaged_quantity": request.POST.get(f"damaged_{line.pk}", 0),
                "missing_quantity": request.POST.get(f"missing_{line.pk}", 0),
                "selling_price": request.POST.get(f"selling_price_{line.pk}") or None,
                "category_id": request.POST.get(f"category_{line.pk}") or None,
                "brand_id": request.POST.get(f"brand_{line.pk}") or None,
            }
            for line in po.lines.all()
        ]
        try:
            receive_purchase_order(po, line_updates)
            messages.success(request, f"PO {po.code} received. Inventory updated.")
            return redirect("procurement_list")
        except Exception as e:
            messages.error(request, str(e))
    return render(
        request,
        "procurement/receive.html",
        {
            "po": po,
            "categories": Category.objects.order_by("name"),
            "brands": Brand.objects.order_by("name"),
        },
    )


# ---------- Inventory ----------


@role_required("Owner", "Warehouse", "Sales", "Operations")
def inventory_list(request):
    q = request.GET.get("q", "")
    items = InventoryItem.objects.all().order_by("name")
    if q:
        items = InventoryItem.objects.filter(
            name__icontains=q
        ) | InventoryItem.objects.filter(sku__icontains=q)
    warehouse = get_main_warehouse()
    store = get_main_store()
    items = list(
        items.prefetch_related("stock_locations__location", "brand", "supplier")
    )
    for item in items:
        item.warehouse_qty = get_stock_quantity(item, warehouse)
        item.store_qty = get_stock_quantity(item, store)
    return render(
        request,
        "inventory/list.html",
        {"items": items, "q": q, "warehouse": warehouse, "store": store},
    )


@role_required("Owner", "Warehouse")
def inventory_create(request):
    form = InventoryItemForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        qty = form.cleaned_data.get("quantity_stocked") or 0
        location = form.cleaned_data.get("warehouse_location") or get_main_warehouse()
        if qty > 0:
            record_stock_movement(
                kind=StockMovement.KIND_PURCHASE,
                item=item,
                quantity=qty,
                destination=location,
                reference=f"STK-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                note="Warehouse stocking form",
                user=request.user if request.user.is_authenticated else None,
            )
        messages.success(request, f"Item {item.sku} added with {qty} units stocked.")
        return redirect("inventory_list")
    return render(
        request, "inventory/form.html", {"form": form, "title": "Add New Item"}
    )


@role_required("Owner", "Warehouse")
def inventory_edit(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    form = InventoryItemForm(request.POST or None, request.FILES or None, instance=item)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        qty = form.cleaned_data.get("quantity_stocked") or 0
        location = form.cleaned_data.get("warehouse_location") or get_main_warehouse()
        if qty > 0:
            record_stock_movement(
                kind=StockMovement.KIND_PURCHASE,
                item=item,
                quantity=qty,
                destination=location,
                reference=f"STK-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                note="Additional warehouse stock",
                user=request.user if request.user.is_authenticated else None,
            )
        messages.success(request, f"Item {item.sku} updated.")
        return redirect("inventory_list")
    return render(
        request,
        "inventory/form.html",
        {
            "form": form,
            "title": f"Edit {item.sku}",
            "item": item,
        },
    )


# ---------- Sales ----------


@role_required("Owner", "Sales", "Finance")
def sales_list(request):
    status_filter = request.GET.get("status", "")
    orders = SalesOrder.objects.select_related("client").order_by("-id")
    if status_filter:
        orders = orders.filter(status=status_filter)
    return render(
        request,
        "sales/list.html",
        {
            "orders": orders,
            "status_choices": SalesOrder.STATUS_CHOICES,
            "current_status": status_filter,
        },
    )


@role_required("Owner", "Sales")
def sales_create(request):
    clients = Client.objects.all().order_by("name")
    store = get_main_store()
    items = list(InventoryItem.objects.all().order_by("name"))
    for item in items:
        item.store_stock = get_stock_quantity(item, store)
    context = {
        "clients": clients,
        "items": items,
        "payment_modes": Payment.MODE_CHOICES,
    }
    if request.method == "POST":
        client_id = request.POST.get("client")
        est_date = request.POST.get("estimated_delivery_date") or None
        allow_override = request.POST.get("allow_no_stock_override") == "on"
        deposit_str = (request.POST.get("deposit", "0") or "0").strip()
        try:
            deposit = Decimal(deposit_str)
        except Exception:
            deposit = Decimal("0")
        if client_id:
            try:
                client = Client.objects.get(pk=int(client_id))
            except (Client.DoesNotExist, ValueError, TypeError):
                messages.error(request, "Please select a valid client.")
                return render(request, "sales/create.html", context)
        else:
            client, _ = Client.objects.get_or_create(
                name="Walk-in Customer",
                defaults={
                    "phone": "-",
                    "email": "walkin@example.com",
                    "credit_limit": 0,
                },
            )
        raw_lines = _parse_lines(request.POST)
        if not raw_lines:
            messages.error(request, "Add at least one order line.")
            return render(request, "sales/create.html", context)
        parsed = []
        for ln in raw_lines:
            try:
                it = InventoryItem.objects.get(pk=ln["item_id"])
                parsed.append(
                    {
                        "item": it,
                        "quantity": ln["quantity"],
                        "unit_price": ln["unit_price"],
                    }
                )
            except InventoryItem.DoesNotExist:
                messages.error(request, "Invalid item selected.")
                return render(request, "sales/create.html", context)
        try:
            order = create_sales_order_with_invoice(
                client=client,
                estimated_delivery_date=est_date,
                allow_override=allow_override,
                lines=parsed,
                deposit=deposit,
                discount_amount=Decimal(request.POST.get("discount", "0") or "0"),
                tax_amount=Decimal(request.POST.get("tax", "0") or "0"),
                payment_method=request.POST.get("payment_method", Payment.MODE_CASH),
                salesperson=request.user if request.user.is_authenticated else None,
            )
            messages.success(
                request, f"Order {order.code} created. Invoice auto-generated."
            )
            return redirect("sales_detail", pk=order.pk)
        except ValidationError as e:
            msg = e.message if hasattr(e, "message") else str(e)
            messages.error(request, msg)
    return render(request, "sales/create.html", context)


@role_required("Owner", "Sales", "Finance")
def sales_detail(request, pk):
    order = get_object_or_404(
        SalesOrder.objects.select_related("client").prefetch_related("lines__item"),
        pk=pk,
    )
    invoice = getattr(order, "invoice", None)
    payments = invoice.payments.all() if invoice else []
    receipts = (
        Receipt.objects.filter(payment__invoice=invoice).order_by("-id")
        if invoice
        else []
    )
    source_quotation = getattr(order, "source_quotation", None)
    return render(
        request,
        "sales/detail.html",
        {
            "order": order,
            "invoice": invoice,
            "payments": payments,
            "receipts": receipts,
            "source_quotation": source_quotation,
            "payment_modes": Payment.MODE_CHOICES,
        },
    )


@role_required("Owner", "Warehouse", "Sales")
def sales_deliver(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    if request.method == "POST":
        try:
            deliver_sales_order(order)
            messages.success(request, f"Order {order.code} marked as delivered.")
        except ValidationError as e:
            msg = e.message if hasattr(e, "message") else str(e)
            messages.error(request, msg)
    return redirect("sales_detail", pk=pk)


@role_required("Owner", "Finance")
def sales_pay_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == "POST":
        amount_str = (request.POST.get("amount", "0") or "0").strip()
        mode = request.POST.get("mode", Payment.MODE_CASH)
        try:
            receipt = create_payment_and_receipt(
                invoice=invoice, amount=Decimal(amount_str), mode=mode
            )
            messages.success(
                request, f"Payment recorded. Receipt {receipt.code} generated."
            )
        except (ValidationError, Exception) as e:
            msg = e.message if hasattr(e, "message") else str(e)
            messages.error(request, msg)
    return redirect("sales_detail", pk=invoice.sales_order.pk)


# ---------- Billing ----------


@role_required("Owner", "Finance")
def billing_overview(request):
    invoices = Invoice.objects.select_related("client", "sales_order").order_by("-id")
    agg = invoices.aggregate(
        ti=Sum("total_amount"), tp=Sum("paid_amount"), tb=Sum("balance")
    )
    return render(
        request,
        "billing/overview.html",
        {
            "invoices": invoices,
            "total_invoiced": agg["ti"] or 0,
            "total_paid": agg["tp"] or 0,
            "total_balance": agg["tb"] or 0,
            "payment_modes": Payment.MODE_CHOICES,
        },
    )


@role_required("Owner", "Finance")
def billing_pay_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == "POST":
        amount_str = (request.POST.get("amount", "0") or "0").strip()
        mode = request.POST.get("mode", Payment.MODE_CASH)
        try:
            receipt = create_payment_and_receipt(
                invoice=invoice, amount=Decimal(amount_str), mode=mode
            )
            messages.success(request, f"Payment saved. Receipt: {receipt.code}")
        except (ValidationError, Exception) as e:
            msg = e.message if hasattr(e, "message") else str(e)
            messages.error(request, msg)
    return redirect("billing_overview")


@role_required("Owner", "Finance")
def billing_expenses(request):
    form = ExpenseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Expense recorded.")
        return redirect("billing_expenses")
    expenses = Expense.objects.select_related("supplier").order_by("-id")
    total = expenses.aggregate(x=Sum("amount")).get("x") or 0
    return render(
        request,
        "billing/expenses.html",
        {"form": form, "expenses": expenses, "total": total},
    )


# ---------- Contacts ----------


@role_required("Owner", "Sales", "Finance")
def contacts_suppliers(request):
    form = SupplierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        s = form.save()
        messages.success(request, f"Supplier '{s.name}' added.")
        return redirect("contacts_suppliers")
    return render(
        request,
        "contacts/suppliers.html",
        {
            "form": form,
            "suppliers": Supplier.objects.all().order_by("name"),
        },
    )


@role_required("Owner", "Sales", "Finance")
def contacts_edit_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Supplier '{supplier.name}' updated.")
        return redirect("contacts_suppliers")
    return render(
        request, "contacts/supplier_form.html", {"form": form, "supplier": supplier}
    )


@role_required("Owner", "Sales", "Finance")
def contacts_clients(request):
    form = ClientForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        c = form.save()
        messages.success(request, f"Client '{c.name}' added.")
        return redirect("contacts_clients")
    return render(
        request,
        "contacts/clients.html",
        {
            "form": form,
            "clients": Client.objects.all().order_by("name"),
        },
    )


@role_required("Owner", "Sales", "Finance")
def contacts_edit_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=client)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Client '{client.name}' updated.")
        return redirect("contacts_clients")
    return render(
        request, "contacts/client_form.html", {"form": form, "client": client}
    )


# ---------- Payroll ----------


@role_required("Owner", "Finance", "Operations")
def payroll_list(request):
    month = request.GET.get("month", "")
    entries = PayrollEntry.objects.all().order_by("-date", "-id")
    if month:
        try:
            year, mo = month.split("-")
            entries = entries.filter(date__year=int(year), date__month=int(mo))
        except ValueError:
            pass
    totals = entries.aggregate(total_pay=Sum("pay_per_role"))
    return render(
        request,
        "payroll/list.html",
        {"entries": entries, "totals": totals, "month": month},
    )


@role_required("Owner", "Finance", "Operations")
def payroll_create(request):
    form = PayrollEntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save()
        messages.success(request, f"Payroll entry for {entry.role} recorded.")
        return redirect("payroll_list")
    return render(request, "payroll/create.html", {"form": form})


# ---------- Mining ----------


@role_required("Owner", "Operations")
def mining_list(request):
    month = request.GET.get("month", "")
    entries = MiningEntry.objects.all().order_by("-date", "-id")
    if month:
        try:
            year, mo = month.split("-")
            entries = entries.filter(date__year=int(year), date__month=int(mo))
        except ValueError:
            pass
    totals = entries.aggregate(
        total_produced=Sum("quantity_produced"),
        total_hours=Sum("hours_worked"),
    )
    return render(
        request,
        "mining/list.html",
        {"entries": entries, "totals": totals, "month": month},
    )


@role_required("Owner", "Operations")
def mining_create(request):
    form = MiningEntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save()
        messages.success(request, f"Production entry for {entry.date} recorded.")
        return redirect("mining_list")
    return render(request, "mining/create.html", {"form": form})


# ---------- Documents ----------


@role_required("Owner", "Finance", "Sales")
def invoice_document(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("client", "sales_order"), id=invoice_id
    )
    return render(
        request,
        "documents/invoice.html",
        {
            "invoice": invoice,
            "order": invoice.sales_order,
            "lines": invoice.sales_order.lines.select_related("item"),
        },
    )


@role_required("Owner", "Finance", "Sales")
def receipt_document(request, receipt_id):
    receipt = get_object_or_404(
        Receipt.objects.select_related(
            "payment", "payment__invoice", "payment__invoice__client"
        ),
        id=receipt_id,
    )
    return render(
        request,
        "documents/receipt.html",
        {
            "receipt": receipt,
            "invoice": receipt.payment.invoice,
            "client": receipt.payment.invoice.client,
        },
    )


# ---------- Quotations ----------


@role_required("Owner", "Sales", "Finance")
def quotation_list(request):
    status_filter = request.GET.get("status", "")
    quotes = (
        Quotation.objects.select_related("client", "converted_sales_order")
        .prefetch_related("lines")
        .order_by("-id")
    )
    if status_filter:
        quotes = quotes.filter(status=status_filter)
    return render(
        request,
        "quotations/list.html",
        {
            "quotes": quotes,
            "status_choices": Quotation.STATUS_CHOICES,
            "current_status": status_filter,
        },
    )


@role_required("Owner", "Sales")
def quotation_create(request):
    clients = Client.objects.all().order_by("name")
    items = InventoryItem.objects.all().order_by("name")
    form = QuotationForm(request.POST or None)
    if request.method == "POST":
        raw_lines = _parse_lines(request.POST)
        if not form.is_valid():
            messages.error(request, "Please correct the errors below.")
        elif not raw_lines:
            messages.error(request, "Add at least one quotation line.")
        else:
            with transaction.atomic():
                quote = form.save(commit=False)
                quote.code = generate_code("QT")
                quote.save()
                for ln in raw_lines:
                    QuotationLine.objects.create(
                        quotation=quote,
                        item_id=ln["item_id"],
                        quantity=ln["quantity"],
                        unit_price=ln["unit_price"],
                    )
            messages.success(request, f"Quotation {quote.code} created.")
            return redirect("quotation_detail", pk=quote.pk)
    return render(
        request,
        "quotations/create.html",
        {"form": form, "clients": clients, "items": items},
    )


@role_required("Owner", "Sales", "Finance")
def quotation_detail(request, pk):
    quote = get_object_or_404(
        Quotation.objects.select_related(
            "client", "converted_sales_order"
        ).prefetch_related("lines__item"),
        pk=pk,
    )
    converted_invoice = None
    converted_receipts = []
    if quote.converted_sales_order_id:
        converted_invoice = getattr(quote.converted_sales_order, "invoice", None)
        if converted_invoice:
            converted_receipts = Receipt.objects.filter(
                payment__invoice=converted_invoice
            ).order_by("-id")
    return render(
        request,
        "quotations/detail.html",
        {
            "quote": quote,
            "status_choices": Quotation.STATUS_CHOICES,
            "converted_invoice": converted_invoice,
            "converted_receipts": converted_receipts,
        },
    )


@role_required("Owner", "Sales")
def quotation_set_status(request, pk):
    quote = get_object_or_404(Quotation, pk=pk)
    if request.method == "POST":
        new_status = request.POST.get("status")
        valid = {s for s, _ in Quotation.STATUS_CHOICES} - {Quotation.STATUS_CONVERTED}
        if new_status in valid and quote.status != Quotation.STATUS_CONVERTED:
            quote.status = new_status
            quote.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Quotation marked as {new_status}.")
        else:
            messages.error(request, "Invalid status change.")
    return redirect("quotation_detail", pk=pk)


@role_required("Owner", "Sales", "Finance")
def quotation_convert(request, pk):
    quote = get_object_or_404(Quotation, pk=pk)
    if request.method == "POST":
        allow_override = request.POST.get("allow_no_stock_override") == "on"
        deposit_str = (request.POST.get("deposit", "0") or "0").strip()
        est_date = request.POST.get("estimated_delivery_date") or None
        try:
            deposit = Decimal(deposit_str)
        except Exception:
            deposit = Decimal("0")
        try:
            order = convert_quotation_to_sales_order(
                quote,
                allow_override=allow_override,
                deposit=deposit,
                estimated_delivery_date=est_date,
            )
            messages.success(
                request,
                f"Quotation {quote.code} converted to order {order.code}. "
                f"Invoice {order.invoice.code} generated.",
            )
            return redirect("sales_detail", pk=order.pk)
        except ValidationError as e:
            msg = e.message if hasattr(e, "message") else str(e)
            messages.error(request, msg)
    return redirect("quotation_detail", pk=pk)


@role_required("Owner", "Sales", "Finance")
def quotation_document(request, pk):
    quote = get_object_or_404(
        Quotation.objects.select_related("client").prefetch_related("lines__item"),
        pk=pk,
    )
    return render(
        request,
        "documents/quotation.html",
        {"quote": quote, "lines": quote.lines.select_related("item")},
    )


# ─── Financial Reports (Owner + Admin only) ───────────────────────────────────


@role_required("Owner", "Admin", "General Manager", "Store Manager")
def reports_overview(request):
    from datetime import date, timedelta

    today = timezone.localdate()
    start_str = request.GET.get("start") or (today - timedelta(days=30)).isoformat()
    end_str = request.GET.get("end") or today.isoformat()

    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
    except ValueError:
        start = today - timedelta(days=30)
        end = today

    inv_q = Invoice.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end
    )
    pay_q = Payment.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end, is_refunded=False
    )
    exp_q = Expense.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end
    )
    pr_q = PayrollEntry.objects.filter(date__gte=start, date__lte=end)
    mn_q = MiningEntry.objects.filter(date__gte=start, date__lte=end)

    invoiced = inv_q.aggregate(s=Sum("total_amount"))["s"] or Decimal("0")
    collected = pay_q.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    expenses_total = exp_q.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    payroll_total = pr_q.aggregate(s=Sum("pay_per_role"))["s"] or Decimal("0")

    ar_total = Invoice.objects.aggregate(s=Sum("balance"))["s"] or Decimal("0")
    overdue_30 = Invoice.objects.filter(
        balance__gt=0, created_at__date__lte=today - timedelta(days=30)
    ).aggregate(s=Sum("balance"))["s"] or Decimal("0")

    sales_net = collected
    inventory_valuation = sum(
        item.stock_on_hand * item.unit_cost for item in InventoryItem.objects.all()
    )
    warehouse = get_main_warehouse()
    store = get_main_store()
    warehouse_stock = list(
        StockLocation.objects.filter(location=warehouse).select_related(
            "item", "location"
        )
    )
    for row in warehouse_stock:
        row.value = row.quantity * row.item.unit_cost
    storefront_stock = list(
        StockLocation.objects.filter(location=store).select_related("item", "location")
    )
    low_stock_items = [
        item
        for item in InventoryItem.objects.all().order_by("name")
        if item.available_stock <= item.reorder_level
    ][:20]
    line_revenue = ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    fast_moving_items = (
        SalesOrderLine.objects.filter(sales_order__actual_delivery_date__gte=start)
        .values("item__sku", "item__name")
        .annotate(qty=Sum("quantity"), revenue=Sum(line_revenue))
        .order_by("-qty")[:10]
    )
    sold_item_ids = SalesOrderLine.objects.values_list("item_id", flat=True).distinct()
    dead_stock_items = list(
        InventoryItem.objects.exclude(id__in=sold_item_ids)
        .filter(stock_on_hand__gt=0)
        .order_by("name")[:20]
    )
    for item in dead_stock_items:
        item.stock_value = item.stock_on_hand * item.unit_cost
    transfer_history = StockMovement.objects.filter(
        kind=StockMovement.KIND_TRANSFER,
        created_at__date__gte=start,
        created_at__date__lte=end,
    ).select_related("item", "source", "destination", "user")[:20]
    supplier_purchase_history = (
        PurchaseOrderLine.objects.filter(
            purchase_order__created_at__date__gte=start,
            purchase_order__created_at__date__lte=end,
        )
        .values("purchase_order__supplier__name")
        .annotate(
            qty=Sum("quantity"),
            total=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_price"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
        )
        .order_by("-total")[:10]
    )

    payments_by_mode = (
        pay_q.values("mode")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    expenses_by_type = (
        exp_q.values("expense_type")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    expenses_by_supplier = (
        exp_q.exclude(supplier__isnull=True)
        .values("supplier__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:10]
    )
    top_clients = (
        inv_q.values("client__name")
        .annotate(total=Sum("total_amount"), paid=Sum("paid_amount"))
        .order_by("-total")[:10]
    )
    payroll_by_role = (
        pr_q.values("role").annotate(total=Sum("pay_per_role")).order_by("-total")
    )
    payroll_by_worker = (
        pr_q.values("worker_name", "role", "department")
        .annotate(total=Sum("pay_per_role"), count=Count("id"))
        .order_by("-total")
    )
    payroll_by_department = (
        pr_q.values("department")
        .annotate(total=Sum("pay_per_role"), count=Count("id"))
        .order_by("department")
    )
    mining_by_mineral = (
        mn_q.values("mineral_type")
        .annotate(qty=Sum("quantity_produced"), hours=Sum("hours_worked"))
        .order_by("-qty")
    )
    outstanding_invoices = (
        Invoice.objects.filter(balance__gt=0)
        .select_related("client")
        .order_by("-balance")[:20]
    )

    return render(
        request,
        "reports/overview.html",
        {
            "start": start,
            "end": end,
            "invoiced": invoiced,
            "collected": collected,
            "expenses_total": expenses_total,
            "payroll_total": payroll_total,
            "sales_net": sales_net,
            "inventory_valuation": inventory_valuation,
            "ar_total": ar_total,
            "overdue_30": overdue_30,
            "payments_by_mode": payments_by_mode,
            "expenses_by_type": expenses_by_type,
            "expenses_by_supplier": expenses_by_supplier,
            "top_clients": top_clients,
            "payroll_by_role": payroll_by_role,
            "payroll_by_worker": payroll_by_worker,
            "payroll_by_department": payroll_by_department,
            "mining_by_mineral": mining_by_mineral,
            "outstanding_invoices": outstanding_invoices,
            "warehouse_stock": warehouse_stock,
            "storefront_stock": storefront_stock,
            "low_stock_items": low_stock_items,
            "fast_moving_items": fast_moving_items,
            "dead_stock_items": dead_stock_items,
            "transfer_history": transfer_history,
            "supplier_purchase_history": supplier_purchase_history,
        },
    )


# ─── Inventory Foundation Views ───────────────────────────────────────────────


@role_required("Owner", "Warehouse", "Operations")
def locations_list(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        code = (request.POST.get("code") or "").strip()
        kind = request.POST.get("kind") or Location.KIND_WAREHOUSE
        parent_id = request.POST.get("parent") or None
        if not name or not code:
            messages.error(request, "Name and code are required.")
        elif Location.objects.filter(code=code).exists():
            messages.error(request, f"Location code '{code}' already exists.")
        else:
            Location.objects.create(
                name=name,
                code=code,
                kind=kind,
                parent_id=parent_id or None,
            )
            messages.success(request, f"Location {code} added.")
        return redirect("locations_list")

    locations = Location.objects.select_related("parent").all()
    return render(
        request,
        "inventory/locations.html",
        {
            "locations": locations,
            "kind_choices": Location.KIND_CHOICES,
        },
    )


@role_required("Owner", "Warehouse", "Operations")
def stock_transfer(request):
    items = InventoryItem.objects.all().order_by("name")
    locations = Location.objects.all()
    if request.method == "POST":
        try:
            item = get_object_or_404(InventoryItem, pk=request.POST.get("item"))
            source = get_object_or_404(Location, pk=request.POST.get("source"))
            destination = get_object_or_404(
                Location, pk=request.POST.get("destination")
            )
            qty = int(request.POST.get("quantity") or 0)
            note = request.POST.get("note", "")
            record_stock_movement(
                kind=StockMovement.KIND_TRANSFER,
                item=item,
                quantity=qty,
                source=source,
                destination=destination,
                reference=f"TRF-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                note=note,
                user=request.user if request.user.is_authenticated else None,
            )
            messages.success(
                request,
                f"Transferred {qty} {item.unit} of {item.sku} from "
                f"{source.code} to {destination.code}.",
            )
            return redirect("stock_movements")
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
        except (ValueError, TypeError):
            messages.error(request, "Invalid form data.")
    return render(
        request,
        "inventory/transfer.html",
        {"items": items, "locations": locations},
    )


@role_required("Owner", "Warehouse", "Operations")
def stock_adjust(request):
    items = InventoryItem.objects.all().order_by("name")
    locations = Location.objects.all()
    if request.method == "POST":
        try:
            item = get_object_or_404(InventoryItem, pk=request.POST.get("item"))
            location = get_object_or_404(Location, pk=request.POST.get("location"))
            direction = request.POST.get("direction")  # "add" or "remove"
            qty = int(request.POST.get("quantity") or 0)
            reason = request.POST.get("reason", "")
            kwargs = dict(
                kind=StockMovement.KIND_ADJUSTMENT,
                item=item,
                quantity=qty,
                reference=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                note=reason,
                user=request.user if request.user.is_authenticated else None,
            )
            if direction == "add":
                kwargs["destination"] = location
            else:
                kwargs["source"] = location
            record_stock_movement(**kwargs)
            messages.success(
                request,
                f"Adjustment recorded: {direction} {qty} {item.unit} of "
                f"{item.sku} at {location.code}.",
            )
            return redirect("stock_movements")
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
        except (ValueError, TypeError):
            messages.error(request, "Invalid form data.")
    return render(
        request,
        "inventory/adjust.html",
        {"items": items, "locations": locations},
    )


@role_required("Owner", "Warehouse", "Operations", "Sales", "Finance")
def stock_movements(request):
    movements = list(
        StockMovement.objects.select_related(
            "item", "source", "destination", "user"
        ).order_by("-created_at")[:300]
    )
    item_balances = {}
    location_balances = {}

    def location_balance(item_id, location_id):
        if not location_id:
            return None
        key = (item_id, location_id)
        if key not in location_balances:
            location_balances[key] = (
                StockLocation.objects.filter(item_id=item_id, location_id=location_id)
                .values_list("quantity", flat=True)
                .first()
                or 0
            )
        return location_balances[key]

    for movement in movements:
        item_balances.setdefault(movement.item_id, movement.item.stock_on_hand)
        movement.source_stock_after = location_balance(
            movement.item_id, movement.source_id
        )
        movement.destination_stock_after = location_balance(
            movement.item_id, movement.destination_id
        )
        if movement.kind == StockMovement.KIND_PURCHASE:
            signed_quantity = movement.quantity
        elif movement.kind == StockMovement.KIND_SALE:
            signed_quantity = -movement.quantity
        elif movement.kind == StockMovement.KIND_ADJUSTMENT:
            signed_quantity = (
                movement.quantity if movement.destination_id else -movement.quantity
            )
        else:
            signed_quantity = 0
        movement.signed_quantity = signed_quantity
        movement.stock_after = item_balances[movement.item_id]
        item_balances[movement.item_id] -= signed_quantity
        if movement.source_id:
            location_balances[
                (movement.item_id, movement.source_id)
            ] += movement.quantity
        if movement.destination_id:
            location_balances[
                (movement.item_id, movement.destination_id)
            ] -= movement.quantity
    return render(
        request,
        "inventory/movements.html",
        {"movements": movements},
    )


# ---------- Stock Requests (Store -> Warehouse) ----------


@role_required("Owner", "Warehouse", "Sales", "Operations")
def stock_request_list(request):
    requests_qs = StockRequest.objects.select_related(
        "item", "source", "destination", "requested_by", "decided_by"
    )
    return render(
        request,
        "inventory/requests/list.html",
        {"requests": requests_qs},
    )


@role_required("Owner", "Sales", "Operations", "Warehouse")
def stock_request_create(request):
    items = InventoryItem.objects.order_by("name")
    if request.method == "POST":
        try:
            item = get_object_or_404(InventoryItem, pk=request.POST.get("item"))
            qty = int(request.POST.get("quantity") or 0)
            note = request.POST.get("note", "")
            if qty <= 0:
                raise ValidationError("Quantity must be > 0")
            warehouse = get_main_warehouse()
            store = get_main_store()
            StockRequest.objects.create(
                item=item,
                quantity=qty,
                source=warehouse,
                destination=store,
                note=note,
                requested_by=request.user if request.user.is_authenticated else None,
            )
            messages.success(request, f"Stock request raised for {qty} x {item.sku}.")
            return redirect("stock_request_list")
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
        except (ValueError, TypeError):
            messages.error(request, "Invalid form data.")
    return render(request, "inventory/requests/create.html", {"items": items})


@role_required("Owner", "Warehouse")
def stock_request_decide(request, pk):
    req = get_object_or_404(StockRequest, pk=pk)
    action = request.POST.get("action")
    if req.status != StockRequest.STATUS_PENDING:
        messages.error(request, "Only pending requests can be decided.")
        return redirect("stock_request_list")
    if action == "approve":
        req.status = StockRequest.STATUS_APPROVED
    elif action == "reject":
        req.status = StockRequest.STATUS_REJECTED
    else:
        messages.error(request, "Unknown action.")
        return redirect("stock_request_list")
    req.decided_by = request.user if request.user.is_authenticated else None
    req.decided_at = timezone.now()
    req.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
    messages.success(request, f"Request REQ-{req.pk} {req.status.lower()}.")
    return redirect("stock_request_list")


@role_required("Owner", "Warehouse")
def stock_request_fulfill(request, pk):
    req = get_object_or_404(StockRequest, pk=pk)
    try:
        fulfill_stock_request(
            req, user=request.user if request.user.is_authenticated else None
        )
        messages.success(request, f"Request REQ-{req.pk} fulfilled.")
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, "message") else str(e))
    return redirect("stock_request_list")


@role_required("Owner", "Sales", "Operations", "Warehouse")
def stock_request_cancel(request, pk):
    req = get_object_or_404(StockRequest, pk=pk)
    if req.status not in (StockRequest.STATUS_PENDING, StockRequest.STATUS_APPROVED):
        messages.error(request, "Only pending/approved requests can be cancelled.")
    else:
        req.status = StockRequest.STATUS_CANCELLED
        req.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Request REQ-{req.pk} cancelled.")
    return redirect("stock_request_list")
