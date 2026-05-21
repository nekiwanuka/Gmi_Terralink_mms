from django.contrib import admin
from django.utils.html import format_html

from .models import (
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
    StockRequest,
    Supplier,
    UserProfile,
)

admin.site.site_header = "GMI Inventory Administration"
admin.site.site_title = "GMI Inventory Admin"
admin.site.index_title = "Enterprise Inventory Control Center"


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 1


class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 1


class QuotationLineInline(admin.TabularInline):
    model = QuotationLine
    extra = 1


class ReadOnlyTimestampsMixin:
    readonly_fields = ("created_at", "updated_at")


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = (
        "business_name",
        "business_phone",
        "business_email",
        "currency_code",
    )
    search_fields = ("business_name", "business_phone", "business_email")


@admin.register(Supplier)
class SupplierAdmin(ReadOnlyTimestampsMixin, admin.ModelAdmin):
    list_display = ("name", "country", "contact_person", "payment_terms", "created_at")
    list_filter = ("country",)
    search_fields = ("name", "contact_person", "payment_terms")


@admin.register(Client)
class ClientAdmin(ReadOnlyTimestampsMixin, admin.ModelAdmin):
    list_display = ("name", "phone", "email", "credit_limit", "outstanding_amount")
    search_fields = ("name", "phone", "email")

    @admin.display(description="Outstanding")
    def outstanding_amount(self, obj):
        return obj.outstanding_balance()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    list_filter = ("parent",)
    search_fields = ("name", "parent__name")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "kind",
        "parent",
        "is_default_warehouse",
        "is_default_store",
    )
    list_filter = ("kind", "is_default_warehouse", "is_default_store")
    search_fields = ("code", "name", "parent__code", "parent__name")


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("code", "client", "status", "quote_date", "valid_until")
    list_filter = ("status",)
    search_fields = ("code", "client__name")
    date_hierarchy = "quote_date"
    inlines = [QuotationLineInline]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "supplier",
        "parent_order",
        "status",
        "expected_shipment_date",
        "received_at",
    )
    list_filter = ("status",)
    search_fields = ("code", "supplier__name", "bill_of_lading", "tracking_details")
    date_hierarchy = "expected_shipment_date"
    inlines = [PurchaseOrderLineInline]


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "client",
        "status",
        "payment_status",
        "payment_method",
        "salesperson",
        "total_due_display",
        "estimated_profit_display",
        "estimated_delivery_date",
        "actual_delivery_date",
    )
    list_filter = ("status", "payment_status", "payment_method", "salesperson")
    search_fields = ("code", "client__name", "salesperson__username")
    date_hierarchy = "sale_datetime"
    inlines = [SalesOrderLineInline]

    @admin.display(description="Total Due")
    def total_due_display(self, obj):
        return obj.total_due

    @admin.display(description="Profit")
    def estimated_profit_display(self, obj):
        return obj.estimated_profit


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "image_preview",
        "sku",
        "name",
        "category",
        "brand",
        "supplier",
        "stock_on_hand",
        "reorder_level",
        "selling_price",
        "status",
    )
    list_filter = ("status", "category_ref", "brand", "supplier")
    search_fields = ("sku", "name", "barcode", "batch_number", "supplier__name")
    readonly_fields = ("stock_on_hand", "reserved_stock", "sold_stock", "image_preview")
    fieldsets = (
        (
            "Product Identity",
            {
                "fields": (
                    "name",
                    "description",
                    "sku",
                    "barcode",
                    "product_image",
                    "image_preview",
                )
            },
        ),
        (
            "Classification",
            {
                "fields": (
                    "category",
                    "category_ref",
                    "brand",
                    "unit",
                    "weight_or_volume",
                    "supplier",
                )
            },
        ),
        (
            "Traceability",
            {
                "fields": (
                    "serial_number_tracking",
                    "batch_number",
                    "date_stocked",
                    "expiry_date",
                    "status",
                )
            },
        ),
        ("Pricing", {"fields": ("unit_cost", "selling_price")}),
        (
            "Stock Controls",
            {
                "fields": (
                    "stock_on_hand",
                    "reserved_stock",
                    "sold_stock",
                    "reorder_level",
                    "warehouse_position",
                )
            },
        ),
    )

    @admin.display(description="Image")
    def image_preview(self, obj):
        if obj.product_image:
            return format_html(
                '<img src="{}" class="gmi-admin-thumb" alt="{}" />',
                obj.product_image.url,
                obj.name,
            )
        return "-"


@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    list_display = ("item", "location", "quantity", "location_kind")
    list_filter = ("location__kind", "location")
    search_fields = ("item__sku", "item__name", "location__code", "location__name")

    @admin.display(description="Location Type")
    def location_kind(self, obj):
        return obj.location.kind


@admin.register(StockMovement)
class StockMovementAdmin(ReadOnlyTimestampsMixin, admin.ModelAdmin):
    list_display = (
        "created_at",
        "kind",
        "item",
        "signed_effect",
        "source",
        "destination",
        "reference",
        "user",
    )
    list_filter = ("kind", "source", "destination", "user")
    search_fields = ("item__sku", "item__name", "reference", "note", "user__username")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Effect")
    def signed_effect(self, obj):
        if obj.kind == StockMovement.KIND_TRANSFER:
            return f"Transfer {obj.quantity}"
        if obj.kind == StockMovement.KIND_SALE or (
            obj.kind == StockMovement.KIND_ADJUSTMENT and obj.source_id
        ):
            return f"-{obj.quantity}"
        return f"+{obj.quantity}"


@admin.register(StockRequest)
class StockRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "item",
        "quantity",
        "source",
        "destination",
        "status",
        "requested_by",
        "decided_by",
        "created_at",
    )
    list_filter = ("status", "source", "destination", "requested_by", "decided_by")
    search_fields = ("item__sku", "item__name", "note", "requested_by__username")
    readonly_fields = ("created_at", "updated_at", "decided_at", "fulfilled_movement")
    date_hierarchy = "created_at"


@admin.register(Invoice)
class InvoiceAdmin(ReadOnlyTimestampsMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "client",
        "sales_order",
        "total_amount",
        "paid_amount",
        "balance",
        "created_at",
    )
    list_filter = ("client",)
    search_fields = ("code", "client__name", "sales_order__code")
    date_hierarchy = "created_at"


@admin.register(Payment)
class PaymentAdmin(ReadOnlyTimestampsMixin, admin.ModelAdmin):
    list_display = (
        "invoice",
        "amount",
        "mode",
        "is_refunded",
        "refunded_by",
        "locked_display",
        "created_at",
    )
    list_filter = ("mode", "is_refunded", "refunded_by")
    search_fields = ("invoice__code", "invoice__client__name")
    date_hierarchy = "created_at"

    @admin.display(boolean=True, description="Locked")
    def locked_display(self, obj):
        return bool(obj and obj.is_locked)

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.is_locked:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.is_locked:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Receipt)
class ReceiptAdmin(ReadOnlyTimestampsMixin, admin.ModelAdmin):
    list_display = ("code", "payment", "created_at")
    search_fields = ("code", "payment__invoice__code", "payment__invoice__client__name")
    date_hierarchy = "created_at"


@admin.register(Expense)
class ExpenseAdmin(ReadOnlyTimestampsMixin, admin.ModelAdmin):
    list_display = ("expense_type", "supplier", "amount", "created_at")
    list_filter = ("expense_type", "supplier")
    search_fields = ("supplier__name", "notes")
    date_hierarchy = "created_at"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "role")


@admin.register(NoticeTask)
class NoticeTaskAdmin(ReadOnlyTimestampsMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "target_role",
        "created_by",
        "completed_by",
        "completed_at",
        "created_at",
    )
    list_filter = ("target_role", "completed_at", "created_by", "completed_by")
    search_fields = ("title", "details", "created_by__username")
    date_hierarchy = "created_at"


@admin.register(PayrollEntry)
class PayrollEntryAdmin(ReadOnlyTimestampsMixin, admin.ModelAdmin):
    list_display = (
        "date",
        "worker_name",
        "department",
        "mining_activity",
        "role",
        "pay_per_role",
        "created_at",
    )
    list_filter = ("department", "role", "mining_activity")
    search_fields = ("worker_name", "department", "mining_activity", "role", "notes")
    date_hierarchy = "date"


@admin.register(MiningEntry)
class MiningEntryAdmin(ReadOnlyTimestampsMixin, admin.ModelAdmin):
    list_display = (
        "date",
        "mineral_type",
        "quantity_produced",
        "hours_worked",
        "production_line",
    )
    list_filter = ("mineral_type", "production_line")
    search_fields = ("mineral_type", "production_line")
    date_hierarchy = "date"
