"""Helper: overwrite core/views.py with the full template-based implementation."""

import pathlib, textwrap

BASE = pathlib.Path(__file__).parent
target = BASE / "core" / "views.py"

content = textwrap.dedent(
    """\
    from decimal import Decimal

    from django.contrib import messages
    from django.contrib.auth import login, logout
    from django.contrib.auth.forms import AuthenticationForm
    from django.core.exceptions import ValidationError
    from django.db import transaction
    from django.db.models import F, Sum
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
        PurchaseOrderForm,
        PurchaseOrderStatusForm,
        SupplierForm,
    )
    from .models import (
        BusinessProfile,
        Client,
        Expense,
        InventoryItem,
        Invoice,
        MiningEntry,
        Payment,
        PurchaseOrder,
        PurchaseOrderLine,
        Receipt,
        SalesOrder,
        Supplier,
        UserProfile,
        create_payment_and_receipt,
        create_sales_order_with_invoice,
        deliver_sales_order,
        generate_code,
        receive_purchase_order,
    )
    from .serializers import (
        ClientSerializer,
        ExpenseSerializer,
        InventoryItemSerializer,
        MiningEntrySerializer,
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
        queryset = Receipt.objects.select_related(
            "payment", "payment__invoice"
        ).order_by("-id")
        serializer_class = ReceiptSerializer


    class ExpenseViewSet(viewsets.ModelViewSet):
        queryset = Expense.objects.select_related("supplier").order_by("-id")
        serializer_class = ExpenseSerializer


    class MiningEntryViewSet(viewsets.ModelViewSet):
        queryset = MiningEntry.objects.all().order_by("-date", "-id")
        serializer_class = MiningEntrySerializer


    # ---------- Internal helpers ----------


    def _get_profile():
        profile, _ = BusinessProfile.objects.get_or_create(id=1)
        return profile


    # Backward-compat alias used by older code paths
    get_profile = _get_profile


    def _build_alerts():
        alerts = []
        for item in InventoryItem.objects.all():
            if item.available_stock <= item.reorder_level:
                alerts.append(
                    f"Low stock: {item.sku} — {item.available_stock} available."
                )
        for inv in Invoice.objects.filter(balance__gt=0):
            alerts.append(
                f"Unpaid invoice {inv.code}: balance UGX {inv.balance:,}."
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
                    lines.append({
                        "item_id": int(item_id),
                        "quantity": int(qty),
                        "unit_price": Decimal(price),
                    })
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


    @role_required("Owner", "Finance", "Warehouse", "Sales", "Operations")
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
        out_of_stock = items.filter(stock_on_hand__lte=F("reserved_stock")).count()
        low_stock = [i for i in items if 0 < i.available_stock <= i.reorder_level]

        now = timezone.localdate()
        month_sales = (
            Payment.objects.filter(
                created_at__year=now.year, created_at__month=now.month
            ).aggregate(x=Sum("amount")).get("x") or 0
        )
        month_output = (
            MiningEntry.objects.filter(
                date__year=now.year, date__month=now.month
            ).aggregate(x=Sum("quantity_produced")).get("x") or 0
        )
        top_customers = (
            Invoice.objects.values("client__name")
            .annotate(total=Sum("total_amount"))
            .order_by("-total")[:5]
        )
        return render(request, "dashboard.html", {
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "outstanding": outstanding,
            "expenses": expenses_total,
            "supplier_dues": supplier_dues,
            "low_stock_count": len(low_stock),
            "out_of_stock_count": out_of_stock,
            "month_sales": month_sales,
            "month_output": month_output,
            "top_customers": top_customers,
            "recent_orders": SalesOrder.objects.select_related("client").order_by("-id")[:10],
            "recent_pos": PurchaseOrder.objects.select_related("supplier").order_by("-id")[:10],
            "alerts": _build_alerts(),
        })


    # ---------- Settings ----------


    @role_required("Owner")
    def settings_page(request):
        profile = _get_profile()
        users = UserProfile.objects.select_related("user").order_by("user__username")
        if request.method == "POST":
            act = request.POST.get("action")
            if act == "profile":
                profile.business_name = request.POST.get("business_name", profile.business_name)
                profile.business_address = request.POST.get(
                    "business_address", profile.business_address
                )
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
        return render(request, "settings.html", {
            "profile": profile,
            "users": users,
            "role_choices": UserProfile.ROLE_CHOICES,
        })


    # ---------- Procurement ----------


    @role_required("Owner", "Warehouse", "Finance")
    def procurement_list(request):
        status_filter = request.GET.get("status", "")
        pos = (
            PurchaseOrder.objects
            .select_related("supplier")
            .prefetch_related("lines")
            .order_by("-id")
        )
        if status_filter:
            pos = pos.filter(status=status_filter)
        return render(request, "procurement/list.html", {
            "pos": pos,
            "status_choices": PurchaseOrder.STATUS_CHOICES,
            "current_status": status_filter,
        })


    @role_required("Owner", "Warehouse")
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


    @role_required("Owner", "Warehouse")
    def procurement_update_status(request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if request.method == "POST":
            form = PurchaseOrderStatusForm(request.POST, instance=po)
            if form.is_valid():
                form.save()
                messages.success(request, f"{po.code} updated.")
        return redirect("procurement_list")


    @role_required("Owner", "Warehouse")
    def warehouse_receive(request, pk):
        po = get_object_or_404(
            PurchaseOrder.objects.prefetch_related("lines__item"), pk=pk
        )
        if request.method == "POST":
            line_updates = [
                {
                    "line": line,
                    "received_quantity": request.POST.get(f"received_{line.pk}", 0),
                    "damaged_quantity": request.POST.get(f"damaged_{line.pk}", 0),
                    "missing_quantity": request.POST.get(f"missing_{line.pk}", 0),
                }
                for line in po.lines.all()
            ]
            try:
                receive_purchase_order(po, line_updates)
                messages.success(request, f"PO {po.code} received. Inventory updated.")
                return redirect("procurement_list")
            except Exception as e:
                messages.error(request, str(e))
        return render(request, "procurement/receive.html", {"po": po})


    # ---------- Inventory ----------


    @role_required("Owner", "Warehouse", "Sales", "Operations")
    def inventory_list(request):
        q = request.GET.get("q", "")
        items = InventoryItem.objects.all().order_by("name")
        if q:
            items = (
                InventoryItem.objects.filter(name__icontains=q)
                | InventoryItem.objects.filter(sku__icontains=q)
            )
        return render(request, "inventory/list.html", {"items": items, "q": q})


    @role_required("Owner", "Warehouse")
    def inventory_create(request):
        form = InventoryItemForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            item = form.save()
            messages.success(request, f"Item {item.sku} added.")
            return redirect("inventory_list")
        return render(request, "inventory/form.html", {
            "form": form, "title": "Add New Item"
        })


    @role_required("Owner", "Warehouse")
    def inventory_edit(request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        form = InventoryItemForm(request.POST or None, instance=item)
        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(request, f"Item {item.sku} updated.")
            return redirect("inventory_list")
        return render(request, "inventory/form.html", {
            "form": form,
            "title": f"Edit {item.sku}",
            "item": item,
        })


    # ---------- Sales ----------


    @role_required("Owner", "Sales", "Finance")
    def sales_list(request):
        status_filter = request.GET.get("status", "")
        orders = SalesOrder.objects.select_related("client").order_by("-id")
        if status_filter:
            orders = orders.filter(status=status_filter)
        return render(request, "sales/list.html", {
            "orders": orders,
            "status_choices": SalesOrder.STATUS_CHOICES,
            "current_status": status_filter,
        })


    @role_required("Owner", "Sales")
    def sales_create(request):
        clients = Client.objects.all().order_by("name")
        items = InventoryItem.objects.all().order_by("name")
        if request.method == "POST":
            client_id = request.POST.get("client")
            est_date = request.POST.get("estimated_delivery_date") or None
            allow_override = request.POST.get("allow_no_stock_override") == "on"
            deposit_str = (request.POST.get("deposit", "0") or "0").strip()
            try:
                deposit = Decimal(deposit_str)
            except Exception:
                deposit = Decimal("0")
            try:
                client = Client.objects.get(pk=int(client_id))
            except (Client.DoesNotExist, ValueError, TypeError):
                messages.error(request, "Please select a valid client.")
                return render(
                    request, "sales/create.html", {"clients": clients, "items": items}
                )
            raw_lines = _parse_lines(request.POST)
            if not raw_lines:
                messages.error(request, "Add at least one order line.")
                return render(
                    request, "sales/create.html", {"clients": clients, "items": items}
                )
            parsed = []
            for ln in raw_lines:
                try:
                    it = InventoryItem.objects.get(pk=ln["item_id"])
                    parsed.append({
                        "item": it,
                        "quantity": ln["quantity"],
                        "unit_price": ln["unit_price"],
                    })
                except InventoryItem.DoesNotExist:
                    messages.error(request, "Invalid item selected.")
                    return render(
                        request, "sales/create.html", {"clients": clients, "items": items}
                    )
            try:
                order = create_sales_order_with_invoice(
                    client=client,
                    estimated_delivery_date=est_date,
                    allow_override=allow_override,
                    lines=parsed,
                    deposit=deposit,
                )
                messages.success(
                    request, f"Order {order.code} created. Invoice auto-generated."
                )
                return redirect("sales_detail", pk=order.pk)
            except ValidationError as e:
                msg = e.message if hasattr(e, "message") else str(e)
                messages.error(request, msg)
        return render(request, "sales/create.html", {"clients": clients, "items": items})


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
        return render(request, "sales/detail.html", {
            "order": order,
            "invoice": invoice,
            "payments": payments,
            "receipts": receipts,
            "payment_modes": Payment.MODE_CHOICES,
        })


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
        return render(request, "billing/overview.html", {
            "invoices": invoices,
            "total_invoiced": agg["ti"] or 0,
            "total_paid": agg["tp"] or 0,
            "total_balance": agg["tb"] or 0,
            "payment_modes": Payment.MODE_CHOICES,
        })


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
        return render(request, "billing/expenses.html", {
            "form": form, "expenses": expenses, "total": total
        })


    # ---------- Contacts ----------


    @role_required("Owner", "Sales", "Finance")
    def contacts_suppliers(request):
        form = SupplierForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            s = form.save()
            messages.success(request, f"Supplier '{s.name}' added.")
            return redirect("contacts_suppliers")
        return render(request, "contacts/suppliers.html", {
            "form": form,
            "suppliers": Supplier.objects.all().order_by("name"),
        })


    @role_required("Owner", "Sales", "Finance")
    def contacts_edit_supplier(request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        form = SupplierForm(request.POST or None, instance=supplier)
        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(request, f"Supplier '{supplier.name}' updated.")
            return redirect("contacts_suppliers")
        return render(request, "contacts/supplier_form.html", {
            "form": form, "supplier": supplier
        })


    @role_required("Owner", "Sales", "Finance")
    def contacts_clients(request):
        form = ClientForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            c = form.save()
            messages.success(request, f"Client '{c.name}' added.")
            return redirect("contacts_clients")
        return render(request, "contacts/clients.html", {
            "form": form,
            "clients": Client.objects.all().order_by("name"),
        })


    @role_required("Owner", "Sales", "Finance")
    def contacts_edit_client(request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = ClientForm(request.POST or None, instance=client)
        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(request, f"Client '{client.name}' updated.")
            return redirect("contacts_clients")
        return render(request, "contacts/client_form.html", {
            "form": form, "client": client
        })


    # ---------- Mining ----------


    @role_required("Owner", "Operations")
    def mining_list(request):
        month = request.GET.get("month", "")
        entries = MiningEntry.objects.all().order_by("-date", "-id")
        if month:
            try:
                year, mo = month.split("-")
                entries = entries.filter(
                    date__year=int(year), date__month=int(mo)
                )
            except ValueError:
                pass
        totals = entries.aggregate(
            total_produced=Sum("quantity_produced"),
            total_hours=Sum("hours_worked"),
            total_labor=Sum("labor_cost"),
        )
        return render(request, "mining/list.html", {
            "entries": entries, "totals": totals, "month": month
        })


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
        return render(request, "documents/invoice.html", {
            "invoice": invoice,
            "order": invoice.sales_order,
            "lines": invoice.sales_order.lines.select_related("item"),
        })


    @role_required("Owner", "Finance", "Sales")
    def receipt_document(request, receipt_id):
        receipt = get_object_or_404(
            Receipt.objects.select_related(
                "payment", "payment__invoice", "payment__invoice__client"
            ),
            id=receipt_id,
        )
        return render(request, "documents/receipt.html", {
            "receipt": receipt,
            "invoice": receipt.payment.invoice,
            "client": receipt.payment.invoice.client,
        })
"""
)

target.write_text(content, encoding="utf-8")
print(f"Written {target} — {len(content)} chars")
