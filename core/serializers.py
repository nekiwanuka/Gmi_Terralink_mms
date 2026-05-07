from decimal import Decimal

from rest_framework import serializers

from .models import (
    Client,
    Expense,
    InventoryItem,
    MiningEntry,
    PayrollEntry,
    Payment,
    PurchaseOrder,
    PurchaseOrderLine,
    Receipt,
    SalesOrder,
    SalesOrderLine,
    Supplier,
    create_payment_and_receipt,
    create_sales_order_with_invoice,
    receive_purchase_order,
)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class ClientSerializer(serializers.ModelSerializer):
    outstanding_balance = serializers.SerializerMethodField()

    def get_outstanding_balance(self, obj):
        return obj.outstanding_balance()

    class Meta:
        model = Client
        fields = "__all__"


class InventoryItemSerializer(serializers.ModelSerializer):
    available_stock = serializers.IntegerField(read_only=True)
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = "__all__"


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderLine
        fields = [
            "id",
            "item",
            "quantity",
            "unit_price",
            "received_quantity",
            "damaged_quantity",
            "missing_quantity",
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = PurchaseOrderLineSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        po = PurchaseOrder.objects.create(**validated_data)
        for line in lines:
            PurchaseOrderLine.objects.create(purchase_order=po, **line)
        return po


class SalesOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrderLine
        fields = ["id", "item", "quantity", "unit_price"]


class SalesOrderSerializer(serializers.ModelSerializer):
    lines = SalesOrderLineSerializer(many=True, write_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            "id",
            "code",
            "client",
            "estimated_delivery_date",
            "actual_delivery_date",
            "status",
            "payment_status",
            "allow_no_stock_override",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "code",
            "actual_delivery_date",
            "status",
            "payment_status",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        client = validated_data["client"]
        estimated_delivery_date = validated_data.get("estimated_delivery_date")
        allow_override = validated_data.get("allow_no_stock_override", False)
        deposit = Decimal(self.context.get("deposit", "0") or "0")

        parsed_lines = []
        for line in lines:
            parsed_lines.append(
                {
                    "item": line["item"],
                    "quantity": line["quantity"],
                    "unit_price": line["unit_price"],
                }
            )

        return create_sales_order_with_invoice(
            client=client,
            estimated_delivery_date=estimated_delivery_date,
            allow_override=allow_override,
            lines=parsed_lines,
            deposit=deposit,
        )


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = "__all__"


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"


class PayrollEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollEntry
        fields = "__all__"


class MiningEntrySerializer(serializers.ModelSerializer):
    output_per_hour = serializers.DecimalField(
        max_digits=12, decimal_places=4, read_only=True
    )

    class Meta:
        model = MiningEntry
        fields = "__all__"


class PurchaseOrderReceiveSerializer(serializers.Serializer):
    lines = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def save(self, **kwargs):
        po = self.context["po"]
        updates = []
        for row in self.validated_data["lines"]:
            line = po.lines.get(id=row["id"])
            updates.append(
                {
                    "line": line,
                    "received_quantity": row.get("received_quantity", 0),
                    "damaged_quantity": row.get("damaged_quantity", 0),
                    "missing_quantity": row.get("missing_quantity", 0),
                }
            )
        receive_purchase_order(po, updates)
        return po


class PaymentCreateWithReceiptSerializer(serializers.Serializer):
    invoice_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    mode = serializers.ChoiceField(choices=Payment.MODE_CHOICES)

    def save(self, **kwargs):
        invoice = self.context["invoice_model"].objects.get(
            id=self.validated_data["invoice_id"]
        )
        return create_payment_and_receipt(
            invoice=invoice,
            amount=self.validated_data["amount"],
            mode=self.validated_data["mode"],
        )
