from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BusinessProfile(models.Model):
    CURRENCY_UGX = "UGX"
    CURRENCY_USD = "USD"
    CURRENCY_EUR = "EUR"
    CURRENCY_GBP = "GBP"
    CURRENCY_KES = "KES"
    CURRENCY_TZS = "TZS"
    CURRENCY_RWF = "RWF"
    CURRENCY_CNY = "CNY"

    CURRENCY_CHOICES = [
        (CURRENCY_UGX, _("UGX - Ugandan Shilling")),
        (CURRENCY_USD, _("USD - US Dollar")),
        (CURRENCY_EUR, _("EUR - Euro")),
        (CURRENCY_GBP, _("GBP - British Pound")),
        (CURRENCY_KES, _("KES - Kenyan Shilling")),
        (CURRENCY_TZS, _("TZS - Tanzanian Shilling")),
        (CURRENCY_RWF, _("RWF - Rwandan Franc")),
        (CURRENCY_CNY, _("CNY - Chinese Yuan")),
    ]

    business_name = models.CharField(max_length=200, default="GMI TERRALINK")
    business_address = models.TextField(
        default="Hamdeen Lwanga Close, Mitala Road\n"
        "Lower Residence, Plot 10/12, Muyenga, Kampala"
    )
    business_phone = models.CharField(max_length=40, default="+256 768 049 940")
    business_email = models.EmailField(default="gmiterralinkinfo@gmail.com")
    business_website = models.CharField(max_length=120, default="www.gmi-terralink.com")
    currency_code = models.CharField(
        max_length=3, choices=CURRENCY_CHOICES, default=CURRENCY_UGX
    )
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)

    def __str__(self):
        return self.business_name


class Supplier(TimeStampedModel):
    COUNTRY_CHOICES = [
        ("China", _("China")),
        ("Uganda", _("Uganda")),
        ("Local", _("Local")),
    ]

    name = models.CharField(max_length=200)
    country = models.CharField(max_length=20, choices=COUNTRY_CHOICES)
    contact_person = models.CharField(max_length=120)
    payment_terms = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Client(TimeStampedModel):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=40)
    email = models.EmailField()
    credit_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def outstanding_balance(self):
        return Invoice.objects.filter(client=self).aggregate(
            total=models.Sum("balance")
        ).get("total") or Decimal("0")

    def __str__(self):
        return self.name


class InventoryItem(TimeStampedModel):
    STATUS_AVAILABLE = "Available"
    STATUS_DAMAGED = "Damaged"
    STATUS_EXPIRED = "Expired"
    STATUS_RESERVED = "Reserved"
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, _("Available")),
        (STATUS_DAMAGED, _("Damaged")),
        (STATUS_EXPIRED, _("Expired")),
        (STATUS_RESERVED, _("Reserved")),
    ]

    sku = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    barcode = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=100)
    category_ref = models.ForeignKey(
        "Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    brand = models.ForeignKey(
        "Brand",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    unit = models.CharField(max_length=50)
    weight_or_volume = models.CharField(max_length=80, blank=True)
    serial_number_tracking = models.BooleanField(default=False)
    batch_number = models.CharField(max_length=120, blank=True)
    supplier = models.ForeignKey(
        "Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_items",
    )
    reorder_level = models.PositiveIntegerField(default=10)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    date_stocked = models.DateField(default=timezone.localdate)
    expiry_date = models.DateField(blank=True, null=True)
    warehouse_position = models.CharField(max_length=120, blank=True)
    product_image = models.ImageField(upload_to="products/", blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE
    )

    stock_on_hand = models.IntegerField(default=0)
    reserved_stock = models.IntegerField(default=0)
    sold_stock = models.IntegerField(default=0)

    @property
    def available_stock(self):
        return max(0, self.stock_on_hand - self.reserved_stock)

    @property
    def stock_status(self):
        if self.available_stock <= 0:
            return "Out of Stock"
        if self.available_stock <= self.reorder_level:
            return "Low Stock"
        return "In Stock"

    def recompute_stock_on_hand(self):
        total = self.stock_locations.aggregate(s=Sum("quantity"))["s"] or 0
        if self.stock_on_hand != total:
            self.stock_on_hand = total
            self.save(update_fields=["stock_on_hand", "updated_at"])
        return total

    def __str__(self):
        return f"{self.sku} - {self.name}"


class PurchaseOrder(TimeStampedModel):
    STATUS_PENDING = "Pending"
    STATUS_SHIPPED = "Shipped"
    STATUS_TRANSIT = "In Transit"
    STATUS_ARRIVED = "Arrived"

    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_SHIPPED, _("Shipped")),
        (STATUS_TRANSIT, _("In Transit")),
        (STATUS_ARRIVED, _("Arrived")),
    ]

    code = models.CharField(max_length=30, unique=True)
    parent_order = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="split_orders",
    )
    split_from_line = models.ForeignKey(
        "PurchaseOrderLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="split_orders",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="purchase_orders"
    )
    expected_shipment_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    bill_of_lading = models.CharField(max_length=200, blank=True)
    tracking_details = models.CharField(max_length=200, blank=True)
    received_at = models.DateTimeField(blank=True, null=True)

    @property
    def total_amount(self):
        return self.lines.aggregate(
            total=Sum(
                models.F("quantity") * models.F("unit_price"),
                output_field=models.DecimalField(max_digits=14, decimal_places=2),
            )
        ).get("total") or Decimal("0")

    @property
    def is_split(self):
        return bool(self.parent_order_id and self.split_from_line_id)

    def __str__(self):
        return self.code


class PurchaseOrderLine(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT, related_name="po_lines"
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)

    received_quantity = models.PositiveIntegerField(default=0)
    damaged_quantity = models.PositiveIntegerField(default=0)
    missing_quantity = models.PositiveIntegerField(default=0)

    def net_received(self):
        return max(
            0, self.received_quantity - self.damaged_quantity - self.missing_quantity
        )


class SalesOrder(TimeStampedModel):
    STATUS_PENDING = "Pending"
    STATUS_PROCESSING = "Processing"
    STATUS_AWAITING = "Awaiting Stock"
    STATUS_DELIVERED = "Delivered"

    PAYMENT_PARTIAL = "Partially Paid"
    PAYMENT_PAID = "Paid"
    MODE_CASH = "Cash"
    MODE_MOBILE = "Mobile Money"
    MODE_BANK = "Bank"

    MODE_CHOICES = [
        (MODE_CASH, _("Cash")),
        (MODE_MOBILE, _("Mobile Money")),
        (MODE_BANK, _("Bank")),
    ]

    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_PROCESSING, _("Processing")),
        (STATUS_AWAITING, _("Awaiting Stock")),
        (STATUS_DELIVERED, _("Delivered")),
    ]

    PAYMENT_CHOICES = [
        (PAYMENT_PARTIAL, _("Partially Paid")),
        (PAYMENT_PAID, _("Paid")),
    ]

    code = models.CharField(max_length=30, unique=True)
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="sales_orders"
    )
    sale_datetime = models.DateTimeField(default=timezone.now)
    estimated_delivery_date = models.DateField(blank=True, null=True)
    actual_delivery_date = models.DateField(blank=True, null=True)

    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_PARTIAL
    )

    allow_no_stock_override = models.BooleanField(default=False)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=20, choices=MODE_CHOICES, default=MODE_CASH
    )
    salesperson = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_orders_created",
    )

    @property
    def subtotal(self):
        return self.lines.aggregate(
            total=Sum(
                models.F("quantity") * models.F("unit_price"),
                output_field=models.DecimalField(max_digits=14, decimal_places=2),
            )
        ).get("total") or Decimal("0")

    @property
    def total_due(self):
        return max(Decimal("0"), self.subtotal - self.discount_amount + self.tax_amount)

    @property
    def estimated_profit(self):
        cost = sum(
            line.quantity * line.item.unit_cost
            for line in self.lines.select_related("item")
        )
        return self.total_due - cost

    def __str__(self):
        return self.code


class SalesOrderLine(models.Model):
    sales_order = models.ForeignKey(
        SalesOrder, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT, related_name="sales_lines"
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    @property
    def line_profit(self):
        return self.line_total - (self.quantity * self.item.unit_cost)


class Quotation(TimeStampedModel):
    STATUS_DRAFT = "Draft"
    STATUS_SENT = "Sent"
    STATUS_ACCEPTED = "Accepted"
    STATUS_REJECTED = "Rejected"
    STATUS_CONVERTED = "Converted"
    STATUS_EXPIRED = "Expired"

    STATUS_CHOICES = [
        (STATUS_DRAFT, _("Draft")),
        (STATUS_SENT, _("Sent")),
        (STATUS_ACCEPTED, _("Accepted")),
        (STATUS_REJECTED, _("Rejected")),
        (STATUS_CONVERTED, _("Converted")),
        (STATUS_EXPIRED, _("Expired")),
    ]

    code = models.CharField(max_length=30, unique=True)
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="quotations"
    )
    quote_date = models.DateField(default=timezone.localdate)
    valid_until = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    notes = models.TextField(blank=True)
    converted_sales_order = models.OneToOneField(
        "SalesOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_quotation",
    )

    @property
    def subtotal(self):
        return self.lines.aggregate(
            total=Sum(
                models.F("quantity") * models.F("unit_price"),
                output_field=models.DecimalField(max_digits=14, decimal_places=2),
            )
        ).get("total") or Decimal("0")

    @property
    def is_convertible(self):
        return self.status not in (
            self.STATUS_CONVERTED,
            self.STATUS_REJECTED,
            self.STATUS_EXPIRED,
        )

    def __str__(self):
        return self.code


class QuotationLine(models.Model):
    quotation = models.ForeignKey(
        Quotation, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT, related_name="quote_lines"
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class Invoice(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    sales_order = models.OneToOneField(
        SalesOrder, on_delete=models.CASCADE, related_name="invoice"
    )
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="invoices"
    )

    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=14, decimal_places=2)

    def recalc(self):
        self.paid_amount = self.payments.filter(is_refunded=False).aggregate(
            total=Sum("amount")
        ).get("total") or Decimal("0")
        self.balance = max(Decimal("0"), self.total_amount - self.paid_amount)
        self.save(update_fields=["paid_amount", "balance", "updated_at"])

    @property
    def is_fully_paid(self):
        """True once the invoice has been settled (balance is zero)."""
        return self.total_amount > 0 and self.balance <= Decimal("0")

    @property
    def is_locked(self):
        """A fully paid invoice is locked: no new payments and existing
        payment entries cannot be edited or deleted."""
        return self.is_fully_paid

    def __str__(self):
        return self.code


class Payment(TimeStampedModel):
    MODE_CASH = "Cash"
    MODE_MOBILE = "Mobile Money"
    MODE_BANK = "Bank"

    MODE_CHOICES = [
        (MODE_CASH, _("Cash")),
        (MODE_MOBILE, _("Mobile Money")),
        (MODE_BANK, _("Bank")),
    ]

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    is_refunded = models.BooleanField(default=False)
    refunded_at = models.DateTimeField(null=True, blank=True)
    refunded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="refunded_payments",
    )

    def clean(self):
        if self.invoice_id and self.amount > self.invoice.balance:
            raise ValidationError("Payment amount cannot exceed invoice balance.")

    @property
    def is_locked(self):
        """A payment is locked once its parent invoice has been fully paid."""
        try:
            return bool(self.invoice and self.invoice.is_locked)
        except Invoice.DoesNotExist:
            return False

    def save(self, *args, **kwargs):
        # Prevent edits to existing payments once the invoice is fully paid.
        if self.pk:
            try:
                original = Payment.objects.get(pk=self.pk)
            except Payment.DoesNotExist:
                original = None
            if original and original.invoice_id and original.invoice.is_fully_paid:
                # Allow no-op saves (same field values) only.
                tracked = ("invoice_id", "amount", "mode", "is_refunded")
                changed = any(getattr(original, f) != getattr(self, f) for f in tracked)
                if changed:
                    raise ValidationError("Payment is locked: invoice is fully paid.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.invoice_id and self.invoice.is_fully_paid:
            raise ValidationError(
                "Payment is locked: invoice is fully paid and cannot be modified."
            )
        return super().delete(*args, **kwargs)


class Receipt(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name="receipt"
    )


class Expense(TimeStampedModel):
    TYPE_SUPPLIER = "Supplier Invoice"
    TYPE_LOGISTICS = "Logistics"
    TYPE_SERVICE = "Local Service"

    TYPE_CHOICES = [
        (TYPE_SUPPLIER, _("Supplier Invoice")),
        (TYPE_LOGISTICS, _("Logistics")),
        (TYPE_SERVICE, _("Local Service")),
    ]

    expense_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True)


class PayrollEntry(TimeStampedModel):
    DEPARTMENT_MINING = "Mining"
    DEPARTMENT_PAYROLL = "Payroll"
    DEPARTMENT_CHOICES = [
        (DEPARTMENT_MINING, _("Mining")),
        (DEPARTMENT_PAYROLL, _("Payroll")),
    ]

    date = models.DateField()
    worker_name = models.CharField(max_length=160, blank=True)
    department = models.CharField(
        max_length=20, choices=DEPARTMENT_CHOICES, default=DEPARTMENT_MINING
    )
    mining_activity = models.CharField(max_length=160, blank=True)
    role = models.CharField(max_length=120)
    pay_per_role = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        label = self.worker_name or self.role
        return f"{label} - {self.date}"


class MiningEntry(TimeStampedModel):
    date = models.DateField()
    mineral_type = models.CharField(max_length=120)
    quantity_produced = models.DecimalField(max_digits=12, decimal_places=2)
    hours_worked = models.DecimalField(max_digits=10, decimal_places=2)
    production_line = models.CharField(max_length=100)

    line_staff_count = models.PositiveIntegerField(default=0)
    expatriates_count = models.PositiveIntegerField(default=0)

    @property
    def output_per_hour(self):
        if self.hours_worked <= 0:
            return Decimal("0")
        return self.quantity_produced / self.hours_worked


def generate_code(prefix):
    return f"{prefix}-{timezone.now().strftime('%y%m%d%H%M%S%f')[-10:]}"


@transaction.atomic
def split_purchase_order_line(*, parent_line, supplier, quantity):
    parent_line = (
        PurchaseOrderLine.objects.select_for_update()
        .select_related("purchase_order", "item")
        .get(pk=parent_line.pk)
    )
    quantity = int(quantity)

    if parent_line.purchase_order.received_at:
        raise ValidationError("Received purchase orders cannot be split.")
    if parent_line.purchase_order.is_split:
        raise ValidationError("Split purchase orders cannot be split again.")
    if supplier.pk == parent_line.purchase_order.supplier_id:
        raise ValidationError("Choose a different supplier for the split quantity.")
    if parent_line.quantity <= 2:
        raise ValidationError(
            "A PO line can only be split when its quantity is more than 2."
        )
    if quantity <= 0:
        raise ValidationError("Split quantity must be at least 1.")
    if quantity >= parent_line.quantity:
        raise ValidationError("Split quantity must leave a balance on the main PO.")

    parent_order = parent_line.purchase_order
    split_po = PurchaseOrder.objects.create(
        code=generate_code("PO"),
        parent_order=parent_order,
        split_from_line=parent_line,
        supplier=supplier,
        expected_shipment_date=parent_order.expected_shipment_date,
        status=parent_order.status,
        bill_of_lading=parent_order.bill_of_lading,
        tracking_details=parent_order.tracking_details,
    )
    PurchaseOrderLine.objects.create(
        purchase_order=split_po,
        item=parent_line.item,
        quantity=quantity,
        unit_price=parent_line.unit_price,
    )

    parent_line.quantity -= quantity
    parent_line.save(update_fields=["quantity"])
    return split_po


@transaction.atomic
def update_purchase_order_split_quantity(*, split_po, quantity):
    split_po = (
        PurchaseOrder.objects.select_for_update()
        .select_related("parent_order", "split_from_line")
        .get(pk=split_po.pk)
    )
    if not split_po.is_split:
        raise ValidationError(
            "Only split purchase orders can have their split quantity edited."
        )
    if split_po.received_at or split_po.parent_order.received_at:
        raise ValidationError(
            "Received purchase orders cannot have split quantities edited."
        )

    split_line = split_po.lines.select_for_update().get()
    parent_line = PurchaseOrderLine.objects.select_for_update().get(
        pk=split_po.split_from_line_id
    )
    quantity = int(quantity)
    total_remaining_for_this_split = parent_line.quantity + split_line.quantity

    if quantity <= 0:
        raise ValidationError("Split quantity must be at least 1.")
    if total_remaining_for_this_split <= 2:
        raise ValidationError(
            "A PO line can only be split when its quantity is more than 2."
        )
    if quantity >= total_remaining_for_this_split:
        raise ValidationError("Split quantity must leave a balance on the main PO.")

    parent_line.quantity = total_remaining_for_this_split - quantity
    split_line.quantity = quantity
    parent_line.save(update_fields=["quantity"])
    split_line.save(update_fields=["quantity"])
    return split_po


def get_stock_quantity(item, location):
    return (
        StockLocation.objects.filter(item=item, location=location)
        .values_list("quantity", flat=True)
        .first()
        or 0
    )


@transaction.atomic
def create_sales_order_with_invoice(
    *,
    client,
    estimated_delivery_date,
    allow_override,
    lines,
    deposit=Decimal("0"),
    discount_amount=Decimal("0"),
    tax_amount=Decimal("0"),
    payment_method=Payment.MODE_CASH,
    salesperson=None,
):
    store = get_main_store()
    order = SalesOrder.objects.create(
        code=generate_code("SO"),
        client=client,
        estimated_delivery_date=estimated_delivery_date,
        allow_no_stock_override=allow_override,
        discount_amount=Decimal(discount_amount or 0),
        tax_amount=Decimal(tax_amount or 0),
        payment_method=payment_method,
        salesperson=salesperson,
    )

    can_fulfill = True
    for line in lines:
        item = line["item"]
        qty = int(line["quantity"])
        price = Decimal(line["unit_price"])

        store_qty = get_stock_quantity(item, store)
        if store_qty <= 0 and not allow_override:
            raise ValidationError(
                f"Cannot sell {item.sku}: storefront stock is 0. "
                "Request a transfer from the warehouse first."
            )

        if store_qty < qty:
            can_fulfill = False

        SalesOrderLine.objects.create(
            sales_order=order,
            item=item,
            quantity=qty,
            unit_price=price,
        )

    order.status = (
        SalesOrder.STATUS_PROCESSING if can_fulfill else SalesOrder.STATUS_AWAITING
    )
    order.save(update_fields=["status", "updated_at"])

    if can_fulfill:
        for line in order.lines.select_related("item"):
            line.item.reserved_stock += line.quantity
            line.item.save(update_fields=["reserved_stock", "updated_at"])

    invoice = Invoice.objects.create(
        code=generate_code("INV"),
        sales_order=order,
        client=client,
        total_amount=order.total_due,
        balance=order.total_due,
    )

    if deposit and deposit > 0:
        create_payment_and_receipt(invoice=invoice, amount=deposit, mode=payment_method)

    return order


@transaction.atomic
def convert_quotation_to_sales_order(
    quotation,
    *,
    allow_override=False,
    deposit=Decimal("0"),
    estimated_delivery_date=None,
):
    if not quotation.is_convertible:
        raise ValidationError(
            f"Quotation {quotation.code} is {quotation.status} and cannot be converted."
        )
    lines = []
    for ql in quotation.lines.select_related("item"):
        lines.append(
            {"item": ql.item, "quantity": ql.quantity, "unit_price": ql.unit_price}
        )
    if not lines:
        raise ValidationError("Quotation has no lines to convert.")

    order = create_sales_order_with_invoice(
        client=quotation.client,
        estimated_delivery_date=estimated_delivery_date,
        allow_override=allow_override,
        lines=lines,
        deposit=Decimal(deposit or 0),
    )
    quotation.status = Quotation.STATUS_CONVERTED
    quotation.converted_sales_order = order
    quotation.save(update_fields=["status", "converted_sales_order", "updated_at"])
    return order


@transaction.atomic
def receive_purchase_order(po, line_updates):
    main_wh = get_main_warehouse()
    for update in line_updates:
        line = update["line"]
        line.received_quantity = int(update["received_quantity"])
        line.damaged_quantity = int(update["damaged_quantity"])
        line.missing_quantity = int(update["missing_quantity"])
        line.save(
            update_fields=["received_quantity", "damaged_quantity", "missing_quantity"]
        )

        net = line.net_received()
        item = line.item
        if net > 0:
            record_stock_movement(
                kind=StockMovement.KIND_PURCHASE,
                item=item,
                quantity=net,
                destination=main_wh,
                reference=po.code,
                note=f"PO receipt {po.code}",
            )

        # Enrichment captured during receipt: pricing + classification
        item_fields = ["unit_cost", "updated_at"]
        item.unit_cost = line.unit_price
        if update.get("selling_price") not in (None, ""):
            item.selling_price = Decimal(str(update["selling_price"]))
            item_fields.append("selling_price")
        if update.get("category_id"):
            item.category_ref_id = update["category_id"]
            item_fields.append("category_ref")
        if update.get("brand_id"):
            item.brand_id = update["brand_id"]
            item_fields.append("brand")
        item.save(update_fields=item_fields)

    po.received_at = timezone.now()
    po.save(update_fields=["received_at", "updated_at"])


@transaction.atomic
def deliver_sales_order(order):
    if order.status == SalesOrder.STATUS_DELIVERED:
        return order

    store = get_main_store()
    for line in order.lines.select_related("item"):
        item = line.item
        store_qty = (
            StockLocation.objects.filter(item=item, location=store)
            .values_list("quantity", flat=True)
            .first()
            or 0
        )
        if store_qty < line.quantity:
            raise ValidationError(
                f"Insufficient stock at {store.code} for {item.sku} "
                f"(available {store_qty}, need {line.quantity}). "
                f"Request a transfer from the warehouse."
            )
        record_stock_movement(
            kind=StockMovement.KIND_SALE,
            item=item,
            quantity=line.quantity,
            source=store,
            reference=order.code,
            note=f"Sales delivery {order.code}",
        )
        item.reserved_stock = max(0, item.reserved_stock - line.quantity)
        item.sold_stock += line.quantity
        item.save(update_fields=["reserved_stock", "sold_stock", "updated_at"])

    order.status = SalesOrder.STATUS_DELIVERED
    order.actual_delivery_date = timezone.localdate()
    order.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    return order


@transaction.atomic
def create_payment_and_receipt(*, invoice, amount, mode):
    amount = Decimal(amount)
    if invoice.is_fully_paid:
        raise ValidationError(
            "Invoice is fully paid and locked. No further payments can be recorded."
        )
    if amount <= 0:
        raise ValidationError("Payment amount must be greater than zero.")
    if amount > invoice.balance:
        raise ValidationError("Payment amount cannot exceed invoice balance.")

    payment = Payment.objects.create(invoice=invoice, amount=amount, mode=mode)
    receipt = Receipt.objects.create(code=generate_code("RCP"), payment=payment)

    invoice.recalc()

    order = invoice.sales_order
    order.payment_status = (
        SalesOrder.PAYMENT_PAID if invoice.balance <= 0 else SalesOrder.PAYMENT_PARTIAL
    )
    order.save(update_fields=["payment_status", "updated_at"])

    return receipt


# ─── User Roles ───────────────────────────────────────────────────────────────


class UserProfile(models.Model):
    ROLE_OWNER = "Owner"
    ROLE_ADMIN = "Admin"
    ROLE_GENERAL_MANAGER = "General Manager"
    ROLE_PROCUREMENT = "Procurement"
    ROLE_FINANCE = "Finance"
    ROLE_WAREHOUSE = "Warehouse"
    ROLE_WAREHOUSE_MANAGER = "Warehouse Manager"
    ROLE_SALES = "Sales"
    ROLE_SALES_ATTENDANT = "Sales Attendant"
    ROLE_STORE_MANAGER = "Store Manager"
    ROLE_OPERATIONS = "Operations"

    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_GENERAL_MANAGER, "General Manager"),
        (ROLE_PROCUREMENT, "Procurement"),
        (ROLE_FINANCE, "Finance"),
        (ROLE_WAREHOUSE, "Warehouse"),
        (ROLE_WAREHOUSE_MANAGER, "Warehouse Manager"),
        (ROLE_SALES, "Sales"),
        (ROLE_SALES_ATTENDANT, "Sales Attendant"),
        (ROLE_STORE_MANAGER, "Store Manager"),
        (ROLE_OPERATIONS, "Operations"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_SALES)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class NoticeTask(TimeStampedModel):
    target_role = models.CharField(max_length=20, choices=UserProfile.ROLE_CHOICES)
    title = models.CharField(max_length=180)
    details = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notice_tasks_created",
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notice_tasks_completed",
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["completed_at", "-created_at"]

    @property
    def is_done(self):
        return self.completed_at is not None

    @property
    def target_label(self):
        if self.target_role == UserProfile.ROLE_OWNER:
            return "Director / Owner"
        return self.get_target_role_display()

    def mark_done(self, user):
        if self.is_done:
            return
        self.completed_by = user
        self.completed_at = timezone.now()
        self.save(update_fields=["completed_by", "completed_at", "updated_at"])

    def __str__(self):
        return f"{self.title} -> {self.target_label}"


# ─── Action Approvals ─────────────────────────────────────────────────────────


class ActionRequest(TimeStampedModel):
    KIND_DELETE = "Delete"
    KIND_REFUND = "Refund"
    KIND_CHOICES = [(KIND_DELETE, KIND_DELETE), (KIND_REFUND, KIND_REFUND)]

    STATUS_PENDING = "Pending"
    STATUS_APPROVED = "Approved"
    STATUS_REJECTED = "Rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, STATUS_PENDING),
        (STATUS_APPROVED, STATUS_APPROVED),
        (STATUS_REJECTED, STATUS_REJECTED),
    ]

    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    target_type = models.CharField(max_length=40)
    target_id = models.PositiveIntegerField()
    target_label = models.CharField(max_length=200)
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="action_requests",
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_action_requests",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} {self.target_type}#{self.target_id} ({self.status})"


# ─── Inventory Foundation: Categories, Brands, Locations, Movements ───────────


class Category(models.Model):
    name = models.CharField(max_length=120)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        ordering = ["name"]
        unique_together = [("name", "parent")]
        verbose_name_plural = "Categories"

    def __str__(self):
        if self.parent_id:
            return f"{self.parent} → {self.name}"
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(models.Model):
    KIND_WAREHOUSE = "Warehouse"
    KIND_STORE = "Store"
    KIND_SECTION = "Section"
    KIND_SHELF = "Shelf"
    KIND_CHOICES = [
        (KIND_WAREHOUSE, KIND_WAREHOUSE),
        (KIND_STORE, KIND_STORE),
        (KIND_SECTION, KIND_SECTION),
        (KIND_SHELF, KIND_SHELF),
    ]

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40, unique=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_WAREHOUSE)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    is_default_warehouse = models.BooleanField(default=False)
    is_default_store = models.BooleanField(default=False)

    class Meta:
        ordering = ["kind", "name"]

    def __str__(self):
        if self.parent_id:
            return f"{self.parent.code} / {self.code}"
        return self.code


class StockLocation(models.Model):
    """Quantity of a given item present at a given location."""

    item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="stock_locations"
    )
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="stock_items"
    )
    quantity = models.IntegerField(default=0)

    class Meta:
        unique_together = [("item", "location")]
        ordering = ["item__name", "location__code"]

    def __str__(self):
        return f"{self.item.sku}@{self.location.code}={self.quantity}"


class StockMovement(TimeStampedModel):
    KIND_PURCHASE = "Purchase"
    KIND_SALE = "Sale"
    KIND_TRANSFER = "Transfer"
    KIND_ADJUSTMENT = "Adjustment"
    KIND_CHOICES = [
        (KIND_PURCHASE, KIND_PURCHASE),
        (KIND_SALE, KIND_SALE),
        (KIND_TRANSFER, KIND_TRANSFER),
        (KIND_ADJUSTMENT, KIND_ADJUSTMENT),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT, related_name="movements"
    )
    quantity = models.IntegerField()
    source = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outbound_movements",
    )
    destination = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inbound_movements",
    )
    reference = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} {self.item.sku} x{self.quantity}"


# ─── Inventory Service Helpers ────────────────────────────────────────────────


def get_main_warehouse():
    """Return the system's default warehouse, creating it on first call."""
    loc, _ = Location.objects.get_or_create(
        is_default_warehouse=True,
        defaults={
            "name": "Main Warehouse",
            "code": "MAIN-WH",
            "kind": Location.KIND_WAREHOUSE,
        },
    )
    return loc


def get_main_store():
    """Return the system's default selling store, creating it on first call."""
    loc, _ = Location.objects.get_or_create(
        is_default_store=True,
        defaults={
            "name": "Main Store",
            "code": "MAIN-STORE",
            "kind": Location.KIND_STORE,
        },
    )
    return loc


def _adjust_stock_location(item, location, delta):
    sl, _ = StockLocation.objects.select_for_update().get_or_create(
        item=item, location=location, defaults={"quantity": 0}
    )
    new_qty = sl.quantity + delta
    if new_qty < 0:
        raise ValidationError(
            f"Insufficient stock for {item.sku} at {location.code} "
            f"(have {sl.quantity}, need {-delta})."
        )
    sl.quantity = new_qty
    sl.save(update_fields=["quantity"])
    return sl


@transaction.atomic
def record_stock_movement(
    *,
    kind,
    item,
    quantity,
    source=None,
    destination=None,
    reference="",
    note="",
    user=None,
):
    """Single source of truth for inventory changes.

    Rules:
      - Purchase: destination required. Adds qty to destination.
      - Sale: source required. Subtracts qty from source.
      - Transfer: source AND destination required. Subtracts source, adds destination.
      - Adjustment: exactly one of source/destination. Positive qty = add at destination
        OR remove at source.
    """
    qty = int(quantity)
    if qty <= 0:
        raise ValidationError("Movement quantity must be positive.")

    if kind == StockMovement.KIND_PURCHASE:
        if not destination:
            raise ValidationError("Purchase requires a destination location.")
        _adjust_stock_location(item, destination, qty)
    elif kind == StockMovement.KIND_SALE:
        if not source:
            raise ValidationError("Sale requires a source location.")
        _adjust_stock_location(item, source, -qty)
    elif kind == StockMovement.KIND_TRANSFER:
        if not source or not destination:
            raise ValidationError("Transfer requires both source and destination.")
        if source.pk == destination.pk:
            raise ValidationError("Transfer source and destination must differ.")
        _adjust_stock_location(item, source, -qty)
        _adjust_stock_location(item, destination, qty)
    elif kind == StockMovement.KIND_ADJUSTMENT:
        if bool(source) == bool(destination):
            raise ValidationError(
                "Adjustment requires exactly one of source or destination."
            )
        if destination:
            _adjust_stock_location(item, destination, qty)
        else:
            _adjust_stock_location(item, source, -qty)
    else:
        raise ValidationError(f"Unknown movement kind: {kind}")

    movement = StockMovement.objects.create(
        kind=kind,
        item=item,
        quantity=qty,
        source=source,
        destination=destination,
        reference=reference,
        note=note,
        user=user,
    )
    item.recompute_stock_on_hand()
    return movement


class StockRequest(models.Model):
    STATUS_PENDING = "Pending"
    STATUS_APPROVED = "Approved"
    STATUS_REJECTED = "Rejected"
    STATUS_FULFILLED = "Fulfilled"
    STATUS_CANCELLED = "Cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, STATUS_PENDING),
        (STATUS_APPROVED, STATUS_APPROVED),
        (STATUS_REJECTED, STATUS_REJECTED),
        (STATUS_FULFILLED, STATUS_FULFILLED),
        (STATUS_CANCELLED, STATUS_CANCELLED),
    ]

    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT, related_name="stock_requests"
    )
    quantity = models.PositiveIntegerField()
    source = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="requests_out"
    )
    destination = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="requests_in"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    note = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_requests_made",
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_requests_decided",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    fulfilled_movement = models.OneToOneField(
        "StockMovement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_request",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"REQ-{self.pk} {self.item.sku} x{self.quantity}"


@transaction.atomic
def fulfill_stock_request(req, user=None):
    if req.status != StockRequest.STATUS_APPROVED:
        raise ValidationError("Only approved requests can be fulfilled.")
    mv = record_stock_movement(
        kind=StockMovement.KIND_TRANSFER,
        item=req.item,
        quantity=req.quantity,
        source=req.source,
        destination=req.destination,
        reference=f"REQ-{req.pk}",
        note=f"Fulfil stock request {req.pk}",
        user=user,
    )
    req.status = StockRequest.STATUS_FULFILLED
    req.fulfilled_movement = mv
    req.save(update_fields=["status", "fulfilled_movement", "updated_at"])
    return mv
