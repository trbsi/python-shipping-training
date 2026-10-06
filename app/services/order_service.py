from collections import defaultdict
from typing import List, Dict

from sqlalchemy.orm import Session

from app.domain.allocation import InventoryItem, allocate_line_item
from app.infrastructure.models import Allocation, Order, OrderLineItem
from app.infrastructure.repositories import (
    get_product_inventory_for_sku_and_customer,
    get_uom_products_by_sku_and_customer,
)


def create_order(
        session: Session, customer_id: int, line_items: List[Dict]
) -> Order:
    """
    Create an order, allocate inventory for all line items, and persist everything.

    Returns the created Order.
    Raises OutOfStock if any line item cannot be fully allocated.
    """
    order = Order(customer_id=customer_id)
    for li in line_items:
        order.line_items.append(OrderLineItem(sku=li["sku"], quantity=li["quantity"]))

    session.add(order)

    skus = [li["sku"] for li in line_items]

    inventory_rows = get_product_inventory_for_sku_and_customer(
        session=session,
        customer_id=customer_id,
        skus=skus,
    )
    uom_product_rows = get_uom_products_by_sku_and_customer(
        session=session,
        customer_id=customer_id,
        skus=skus,
    )

    # Group inventory rows and UoM products by sku
    inventory_rows_by_sku = defaultdict(list)
    for inventory in inventory_rows:
        inventory_rows_by_sku[inventory.sku].append(inventory)

    uom_products_by_sku = defaultdict(list)
    for uom_product in uom_product_rows:
        uom_products_by_sku[uom_product.sku].append(uom_product)

    for li in line_items:
        sku_inventory_rows = inventory_rows_by_sku[li["sku"]]
        inventory_by_id = {inventory.id: inventory for inventory in sku_inventory_rows}
        inventory_items = [
            InventoryItem(
                id=inventory.id,
                sku=inventory.sku,
                uom=inventory.uom,
                quantity=inventory.quantity,
                location_identifier=inventory.location_identifier,
            )
            for inventory in sku_inventory_rows
        ]

        # Prepare UoM products in form of: {"pallet": 1200, "case": 500}
        uom_products = {
            uom_product.uom: uom_product.ea_qty
            for uom_product in uom_products_by_sku[li["sku"]]
        }

        allocations = allocate_line_item(
            inventory_items=inventory_items,
            uom_products=uom_products,
            sku=li["sku"],
            requested_qty=li["quantity"],
        )

        for allocation in allocations:
            order.allocations.append(
                Allocation(
                    customer_id=customer_id,
                    sku=allocation.sku,
                    location_identifier=allocation.location_identifier,
                    quantity=allocation.quantity,
                    uom=allocation.uom,
                )
            )

        # Update quantity in product_inventory
        for inventory_item in inventory_items:
            inventory_by_id[inventory_item.id].quantity = inventory_item.quantity

    return order
