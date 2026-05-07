from django import forms

from .models import (
    Brand,
    Category,
    Client,
    Expense,
    InventoryItem,
    Location,
    MiningEntry,
    PayrollEntry,
    PurchaseOrder,
    PurchaseOrderLine,
    Quotation,
    Supplier,
)


class _StyledMixin:
    """Add form-input CSS class to every widget automatically."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            cls = w.attrs.get("class", "")
            w.attrs["class"] = f"{cls} form-input".strip()


class SupplierForm(_StyledMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "country", "contact_person", "payment_terms"]


class ClientForm(_StyledMixin, forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "phone", "email", "credit_limit"]


class InventoryItemForm(_StyledMixin, forms.ModelForm):
    quantity_stocked = forms.IntegerField(min_value=0, initial=0, required=False)
    warehouse_location = forms.ModelChoiceField(
        queryset=Location.objects.none(), required=False
    )

    UNIT_CHOICES = [
        ("Piece", "Piece"),
        ("Box", "Box"),
        ("Kg", "Kg"),
        ("Litre", "Litre"),
        ("Metre", "Metre"),
        ("Pack", "Pack"),
        ("Set", "Set"),
    ]

    unit = forms.ChoiceField(choices=UNIT_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category_ref"].queryset = Category.objects.order_by("name")
        self.fields["brand"].queryset = Brand.objects.order_by("name")
        self.fields["warehouse_location"].queryset = Location.objects.filter(
            kind__in=[
                Location.KIND_WAREHOUSE,
                Location.KIND_SECTION,
                Location.KIND_SHELF,
            ]
        ).order_by("kind", "name")
        self.fields["warehouse_location"].empty_label = "Main Warehouse"
        self.fields["supplier"].empty_label = "No supplier selected"
        if self.instance and self.instance.pk:
            self.fields["quantity_stocked"].initial = 0

    class Meta:
        model = InventoryItem
        fields = [
            "name",
            "description",
            "sku",
            "barcode",
            "category",
            "category_ref",
            "brand",
            "unit",
            "weight_or_volume",
            "serial_number_tracking",
            "batch_number",
            "supplier",
            "unit_cost",
            "selling_price",
            "date_stocked",
            "expiry_date",
            "quantity_stocked",
            "reorder_level",
            "warehouse_location",
            "warehouse_position",
            "product_image",
            "status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "date_stocked": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "expiry_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class PurchaseOrderForm(_StyledMixin, forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            "supplier",
            "expected_shipment_date",
            "bill_of_lading",
            "tracking_details",
        ]
        widgets = {
            "expected_shipment_date": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
        }


class PurchaseOrderStatusForm(_StyledMixin, forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["status", "bill_of_lading", "tracking_details"]


class ExpenseForm(_StyledMixin, forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["expense_type", "supplier", "amount", "notes"]


class PayrollEntryForm(_StyledMixin, forms.ModelForm):
    class Meta:
        model = PayrollEntry
        fields = [
            "date",
            "worker_name",
            "department",
            "mining_activity",
            "role",
            "pay_per_role",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class MiningEntryForm(_StyledMixin, forms.ModelForm):
    class Meta:
        model = MiningEntry
        fields = [
            "date",
            "mineral_type",
            "quantity_produced",
            "hours_worked",
            "production_line",
            "line_staff_count",
            "expatriates_count",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class QuotationForm(_StyledMixin, forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ["client", "quote_date", "valid_until", "notes"]
        widgets = {
            "quote_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "valid_until": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
