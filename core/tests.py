from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import (
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
    split_purchase_order_line,
    update_purchase_order_split_quantity,
)


class PurchaseOrderSplitTests(TestCase):
    def setUp(self):
        self.main_supplier = Supplier.objects.create(
            name="Main Supplier",
            country="Uganda",
            contact_person="Buyer One",
            payment_terms="Cash",
        )
        self.split_supplier = Supplier.objects.create(
            name="Split Supplier",
            country="Uganda",
            contact_person="Buyer Two",
            payment_terms="Cash",
        )
        self.item = InventoryItem.objects.create(
            sku="CHAIR-001",
            name="Chair",
            category="Furniture",
            unit="Piece",
            unit_cost=Decimal("10.00"),
            selling_price=Decimal("15.00"),
        )
        self.po = PurchaseOrder.objects.create(
            code="PO-TEST-001",
            supplier=self.main_supplier,
            expected_shipment_date=timezone.localdate(),
        )
        self.line = PurchaseOrderLine.objects.create(
            purchase_order=self.po,
            item=self.item,
            quantity=12,
            unit_price=Decimal("10.00"),
        )

    def test_split_creates_child_po_and_leaves_balance_on_main_po(self):
        split_po = split_purchase_order_line(
            parent_line=self.line,
            supplier=self.split_supplier,
            quantity=6,
        )

        self.line.refresh_from_db()
        split_line = split_po.lines.get()

        self.assertEqual(self.line.quantity, 6)
        self.assertEqual(split_line.quantity, 6)
        self.assertEqual(split_po.parent_order, self.po)
        self.assertEqual(split_po.split_from_line, self.line)
        self.assertEqual(self.po.total_amount, Decimal("60"))
        self.assertEqual(split_po.total_amount, Decimal("60"))

    def test_split_quantity_edit_rebalances_main_po(self):
        split_po = split_purchase_order_line(
            parent_line=self.line,
            supplier=self.split_supplier,
            quantity=6,
        )

        update_purchase_order_split_quantity(split_po=split_po, quantity=4)

        self.line.refresh_from_db()
        split_line = split_po.lines.get()
        self.assertEqual(self.line.quantity, 8)
        self.assertEqual(split_line.quantity, 4)

        with self.assertRaises(ValidationError):
            update_purchase_order_split_quantity(split_po=split_po, quantity=12)

    def test_split_requires_more_than_two_items_and_main_balance(self):
        self.line.quantity = 2
        self.line.save(update_fields=["quantity"])

        with self.assertRaises(ValidationError):
            split_purchase_order_line(
                parent_line=self.line,
                supplier=self.split_supplier,
                quantity=1,
            )

        self.line.quantity = 12
        self.line.save(update_fields=["quantity"])
        with self.assertRaises(ValidationError):
            split_purchase_order_line(
                parent_line=self.line,
                supplier=self.split_supplier,
                quantity=12,
            )
