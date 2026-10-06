import pytest

from app.domain.allocation import InventoryItem, allocate_line_item as allocate_from_inventory
from app.domain.exceptions import OutOfStock
from app.infrastructure.repositories import (
    get_product_inventory_for_sku_and_customer,
    get_uom_products_by_sku_and_customer,
)
from conftest import seed_inventory, seed_uom


def allocate_line_item(session, customer_id: int, sku: str, requested_qty: int):
    inventory_rows = get_product_inventory_for_sku_and_customer(
        session=session,
        customer_id=customer_id,
        skus=[sku],
    )
    uom_products = get_uom_products_by_sku_and_customer(
        session=session,
        customer_id=customer_id,
        skus=[sku],
    )
    inventory_by_id = {inventory.id: inventory for inventory in inventory_rows}
    inventory_items = [
        InventoryItem(
            id=inventory.id,
            sku=inventory.sku,
            uom=inventory.uom,
            quantity=inventory.quantity,
            location_identifier=inventory.location_identifier,
        )
        for inventory in inventory_rows
    ]
    uom_products = {
        uom_product.uom: uom_product.ea_qty
        for uom_product in uom_products
    }

    allocations = allocate_from_inventory(
        inventory_items=inventory_items,
        uom_products=uom_products,
        sku=sku,
        requested_qty=requested_qty,
    )

    for inventory_item in inventory_items:
        inventory_by_id[inventory_item.id].quantity = inventory_item.quantity

    return allocations


# ── Basic allocation ─────────────────────────────────────────────────────


def test_allocate_eaches_only(session):
    """Allocate from eaches-only inventory (no UoM conversion)."""
    seed_inventory(
        session, customer_id=1, sku="widget", uom=None, quantity=500, location="loc-1"
    )

    allocs = allocate_line_item(session, customer_id=1, sku="widget", requested_qty=200)

    assert len(allocs) == 1
    assert allocs[0].quantity == 200
    assert allocs[0].uom is None
    assert allocs[0].location_identifier == "loc-1"


def test_allocate_pallets_before_eaches(session):
    """Pallets are consumed before eaches (largest UoM first)."""
    seed_inventory(
        session,
        customer_id=1,
        sku="tshirt",
        uom="pallet",
        quantity=10,
        location="loc-1",
    )
    seed_inventory(
        session, customer_id=1, sku="tshirt", uom=None, quantity=1000, location="loc-2"
    )
    seed_uom(session, customer_id=1, sku="tshirt", uom="pallet", ea_qty=100)

    allocs = allocate_line_item(session, customer_id=1, sku="tshirt", requested_qty=250)

    pallet_allocs = [a for a in allocs if a.uom == "pallet"]
    each_allocs = [a for a in allocs if a.uom is None]

    assert sum(a.quantity for a in pallet_allocs) == 200  # 2 whole pallets
    assert sum(a.quantity for a in each_allocs) == 50


def test_allocate_whole_pallets_only(session):
    """Only whole pallet units are allocated — no partial pallets."""
    seed_inventory(
        session,
        customer_id=1,
        sku="tshirt",
        uom="pallet",
        quantity=10,
        location="loc-1",
    )
    seed_inventory(
        session, customer_id=1, sku="tshirt", uom=None, quantity=1000, location="loc-2"
    )
    seed_uom(session, customer_id=1, sku="tshirt", uom="pallet", ea_qty=100)

    allocs = allocate_line_item(session, customer_id=1, sku="tshirt", requested_qty=150)

    pallet_allocs = [a for a in allocs if a.uom == "pallet"]
    each_allocs = [a for a in allocs if a.uom is None]

    assert sum(a.quantity for a in pallet_allocs) == 100  # 1 whole pallet, NOT 1.5
    assert sum(a.quantity for a in each_allocs) == 50


# ── Mixed UoMs ───────────────────────────────────────────────────────────


def test_allocate_mixed_uom_pallet_case_each(session):
    """Full UoM priority chain: pallet -> case -> each."""
    seed_inventory(
        session, customer_id=1, sku="mug", uom="pallet", quantity=2, location="loc-1"
    )
    seed_inventory(
        session, customer_id=1, sku="mug", uom="case", quantity=10, location="loc-2"
    )
    seed_inventory(
        session, customer_id=1, sku="mug", uom=None, quantity=500, location="loc-3"
    )
    seed_uom(session, customer_id=1, sku="mug", uom="pallet", ea_qty=100)
    seed_uom(session, customer_id=1, sku="mug", uom="case", ea_qty=10)

    allocs = allocate_line_item(session, customer_id=1, sku="mug", requested_qty=235)

    pallet_allocs = [a for a in allocs if a.uom == "pallet"]
    case_allocs = [a for a in allocs if a.uom == "case"]
    each_allocs = [a for a in allocs if a.uom is None]

    assert sum(a.quantity for a in pallet_allocs) == 200  # 2 pallets
    assert sum(a.quantity for a in case_allocs) == 30  # 3 cases
    assert sum(a.quantity for a in each_allocs) == 5  # 5 eaches


def test_readme_example(session):
    """The exact scenario from the README must produce the expected allocations."""
    seed_inventory(
        session,
        customer_id=1,
        sku="tshirt-blue",
        uom=None,
        quantity=1000,
        location="loc-1",
    )
    seed_inventory(
        session,
        customer_id=1,
        sku="tshirt-blue",
        uom="pallet",
        quantity=10,
        location="loc-2",
    )
    seed_uom(session, customer_id=1, sku="tshirt-blue", uom="pallet", ea_qty=1200)

    allocs = allocate_line_item(
        session, customer_id=1, sku="tshirt-blue", requested_qty=2500
    )

    pallet_allocs = [a for a in allocs if a.uom == "pallet"]
    each_allocs = [a for a in allocs if a.uom is None]

    assert sum(a.quantity for a in pallet_allocs) == 2400  # 2 pallets * 1200
    assert pallet_allocs[0].location_identifier == "loc-2"
    assert sum(a.quantity for a in each_allocs) == 100
    assert each_allocs[0].location_identifier == "loc-1"


# ── Error cases ──────────────────────────────────────────────────────────


def test_allocate_insufficient_inventory_raises(session):
    """Must raise OutOfStock when inventory can't satisfy the full quantity."""
    seed_inventory(
        session, customer_id=1, sku="widget", uom=None, quantity=50, location="loc-1"
    )

    with pytest.raises(OutOfStock) as exc_info:
        allocate_line_item(session, customer_id=1, sku="widget", requested_qty=100)

    assert exc_info.value.sku == "widget"
    assert exc_info.value.requested == 100
    assert exc_info.value.available == 50


def test_allocate_no_inventory_raises(session):
    """Requesting a SKU with zero inventory must raise OutOfStock."""

    with pytest.raises(OutOfStock):
        allocate_line_item(session, customer_id=1, sku="ghost", requested_qty=1)


# ── Inventory deduction ─────────────────────────────────────────────────


def test_allocate_deducts_eaches_inventory(session):
    """After allocation, eaches inventory quantity must be reduced."""
    inv = seed_inventory(
        session, customer_id=1, sku="widget", uom=None, quantity=500, location="loc-1"
    )

    allocate_line_item(session, customer_id=1, sku="widget", requested_qty=200)

    assert inv.quantity == 300


def test_allocate_deducts_pallet_inventory_in_uom_units(session):
    """Pallet inventory is deducted in pallet units, not eaches."""
    inv = seed_inventory(
        session,
        customer_id=1,
        sku="tshirt",
        uom="pallet",
        quantity=10,
        location="loc-1",
    )
    seed_inventory(
        session, customer_id=1, sku="tshirt", uom=None, quantity=1000, location="loc-2"
    )
    seed_uom(session, customer_id=1, sku="tshirt", uom="pallet", ea_qty=100)

    allocate_line_item(session, customer_id=1, sku="tshirt", requested_qty=300)

    assert inv.quantity == 7  # 10 - 3 pallets used


# ── Multi-tenant isolation ───────────────────────────────────────


def test_allocate_multi_customer_isolation(session):
    """Allocation for customer 1 must NOT consume customer 2's inventory."""
    seed_inventory(
        session, customer_id=1, sku="tshirt", uom=None, quantity=50, location="loc-1"
    )
    seed_inventory(
        session, customer_id=2, sku="tshirt", uom=None, quantity=500, location="loc-2"
    )

    # Customer 1 only has 50 — requesting 100 must fail
    with pytest.raises(OutOfStock):
        allocate_line_item(session, customer_id=1, sku="tshirt", requested_qty=100)


def test_when_uom_product_have_multiple_customers(session):
    cust_1_pallet = seed_inventory(
        session, customer_id=1, sku="mug", uom="pallet", quantity=2, location="loc-1"
    )
    cust_1_case = seed_inventory(
        session, customer_id=1, sku="mug", uom="case", quantity=10, location="loc-2"
    )
    cust_1_each = seed_inventory(
        session, customer_id=1, sku="mug", uom=None, quantity=500, location="loc-3"
    )
    cust_2_pallet = seed_inventory(
        session, customer_id=2, sku="mug", uom="pallet", quantity=29, location="loc-1"
    )
    cust_2_case = seed_inventory(
        session, customer_id=2, sku="mug", uom="case", quantity=109, location="loc-2"
    )
    cust_2_each = seed_inventory(
        session, customer_id=2, sku="mug", uom=None, quantity=509, location="loc-3"
    )
    seed_uom(session, customer_id=1, sku="mug", uom="pallet", ea_qty=100)
    seed_uom(session, customer_id=1, sku="mug", uom="case", ea_qty=10)
    seed_uom(session, customer_id=2, sku="mug", uom="pallet", ea_qty=999)
    seed_uom(session, customer_id=2, sku="mug", uom="case", ea_qty=99)

    allocs = allocate_line_item(session, customer_id=1, sku="mug", requested_qty=235)

    pallet_allocs = [a for a in allocs if a.uom == "pallet"]
    case_allocs = [a for a in allocs if a.uom == "case"]
    each_allocs = [a for a in allocs if a.uom is None]

    assert sum(a.quantity for a in pallet_allocs) == 200  # 2 pallets
    assert sum(a.quantity for a in case_allocs) == 30  # 3 cases
    assert sum(a.quantity for a in each_allocs) == 5  # 5 eaches

    assert cust_1_pallet.quantity == 0
    assert cust_1_case.quantity == 7
    assert cust_1_each.quantity == 495

    assert cust_2_pallet.quantity == 29
    assert cust_2_case.quantity == 109
    assert cust_2_each.quantity == 509


def test_allocate_uses_multiple_locations_for_same_sku_and_uom(session):
    """Allocation can use the same SKU/UoM from more than one location"""
    loc_1 = seed_inventory(
        session, customer_id=1, sku="widget", uom=None, quantity=80, location="loc-1"
    )
    loc_2 = seed_inventory(
        session, customer_id=1, sku="widget", uom=None, quantity=70, location="loc-2"
    )

    allocs = allocate_line_item(session, customer_id=1, sku="widget", requested_qty=120)

    assert len(allocs) == 2
    assert loc_1.quantity == 0
    assert loc_2.quantity == 30


def test_product_inventory_has_uom_but_uom_products_row_is_missing(session):
    """For example, product_inventory has uom="pallet" but no uom_products row for pallet."""
    inv = seed_inventory(
        session,
        customer_id=1,
        sku="tshirt",
        uom="pallet",
        quantity=1,
        location="loc-1",
    )

    with pytest.raises(OutOfStock) as exc_info:
        allocate_line_item(session, customer_id=1, sku="tshirt", requested_qty=50)

    assert exc_info.value.available == 0
    assert inv.quantity == 1


def test_uom_products_has_uom_but_product_inventory_row_is_missing(session):
    """For example, product_inventory has uom="pallet" but no uom_products row for pallet."""
    seed_uom(session, customer_id=1, sku="tshirt", uom="pallet", ea_qty=100)

    with pytest.raises(OutOfStock) as exc_info:
        allocate_line_item(session, customer_id=1, sku="tshirt", requested_qty=50)

    assert exc_info.value.available == 0
