from app.domain.data_classes import InventoryItem, Allocation
from app.domain.exceptions import OutOfStock

PALLET = 'pallet'
CASE = 'case'
EACH = None


def allocate_line_item(
        inventory_items: list[InventoryItem],
        uom_products: dict[str, int],
        sku: str,
        requested_qty: int,
) -> list[Allocation]:
    """
    Allocate inventory for a single line item (see Goal 2 in the README).

    Returns a list of allocations.
    Raises OutOfStock if inventory cannot satisfy the full requested quantity.
    """
    remaining = requested_qty

    # Calculate total available stock
    check_total_available_stock(
        inventory_items=inventory_items,
        uom_products=uom_products,
        sku=sku,
        requested_qty=requested_qty
    )

    # apply allocation rules
    allocations, remaining = apply_allocation_rules(
        remaining=remaining,
        uom_products=uom_products,
        sku=sku,
        inventory_items=inventory_items
    )

    """
    Even though we may have allocated some stock, we did not allocate the full requested quantity, so this order must fail
    
    For example:
    Inventory:
    1 pallet = 100 eaches
    No eaches
    
    Request:
    50 eaches
    
    Total available is 100, but you cannot allocate half a pallet. So allocation leaves:
    remaining = 50
    and raises OutOfStock.
    """
    if remaining > 0:
        raise OutOfStock(sku, requested_qty, requested_qty - remaining)

    return allocations


def check_total_available_stock(
        inventory_items: list[InventoryItem],
        uom_products: dict,
        sku: str,
        requested_qty: int
) -> None:
    total_stock_available = 0
    for inventory in inventory_items:
        if inventory.uom in uom_products:
            # total stock available + amount of items in pallet/case * number of pallets/cases
            total_stock_available = total_stock_available + uom_products[inventory.uom] * inventory.quantity
        elif inventory.uom is None:
            # total stock available + number of each items
            total_stock_available = total_stock_available + inventory.quantity

    # if we don't have enough items in stock throw exception
    if total_stock_available < requested_qty:
        raise OutOfStock(sku, requested_qty, total_stock_available)


def apply_allocation_rules(
        remaining: int,
        uom_products: dict,
        sku: str,
        inventory_items: list[InventoryItem]
) -> tuple[list[Allocation], int]:
    allocations = []
    uoms = [PALLET, CASE, EACH]
    for uom in uoms:
        if remaining <= 0:
            break

        # determine conversion factor (ea_qty)
        ea_qty = 1
        if uom in uom_products:
            ea_qty = uom_products[uom]

        # get inventory rows for this UoM
        inventories: list[InventoryItem] = [
            inventory for inventory in inventory_items
            if inventory.uom == uom
        ]

        for inventory in inventories:
            if remaining <= 0:
                break

            # convert stock to eaches
            # Step 1: 10 * 1200 = 12_000
            # Step 2: 1000 * 1 = 1000
            available_eaches = inventory.quantity * ea_qty

            if available_eaches <= 0:
                continue

            # take as much as possible
            # Step 1: min(12_000, 2500)
            # Step 2: min(1000, 100)
            take_eaches = min(available_eaches, remaining)

            # enforce FULL UoM usage (round down)
            # Step 1: 2500 // 1200 = 2.08 = 2
            # Step 1: 100 // 1 = 100
            usable_uom_units = take_eaches // ea_qty

            if usable_uom_units == 0:
                continue

            # Step 1: 2 * 1200 = 2400
            # Step 1: 100 * 1 = 100
            final_eaches = usable_uom_units * ea_qty

            # create allocation
            allocations.append(
                Allocation(
                    inventory_id=inventory.id,
                    sku=sku,
                    location_identifier=inventory.location_identifier,
                    quantity=final_eaches,
                    uom=uom
                )
            )

            # reduce inventory + remaining demand
            # Step 1: 10 - 2 = 8
            # Step 2: 1000 - 100 = 900
            inventory.quantity -= usable_uom_units
            # Step 1: 2500 - 2400 = 100
            # Step 1: 100 - 100 = 0
            remaining -= final_eaches

    return allocations, remaining
