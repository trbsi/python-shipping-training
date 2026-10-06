import json

from app.infrastructure.models import Allocation, Order, ProductInventory
from conftest import seed_inventory


def test_create_order_success(client, session):
    """POST /orders/create succeeds with an order_id when inventory is sufficient."""
    seed_inventory(
        session, customer_id=1, sku="tshirt", uom=None, quantity=500, location="loc-1"
    )

    resp = client.post(
        "/orders/create",
        data=json.dumps(
            {
                "customer_id": 1,
                "line_items": [{"sku": "tshirt", "quantity": 100}],
            }
        ),
        content_type="application/json",
    )

    assert resp.status_code in (200, 201)
    data = resp.get_json()
    assert "order_id" in data
    assert isinstance(data["order_id"], int)


def test_create_order_persists_allocations(client, session):
    """Allocations are persisted and linked to the order."""
    seed_inventory(
        session, customer_id=1, sku="tshirt", uom=None, quantity=500, location="loc-1"
    )

    resp = client.post(
        "/orders/create",
        data=json.dumps(
            {
                "customer_id": 1,
                "line_items": [{"sku": "tshirt", "quantity": 100}],
            }
        ),
        content_type="application/json",
    )

    order_id = resp.get_json()["order_id"]
    order = session.get(Order, order_id)
    assert len(order.allocations) == 1
    assert order.allocations[0].quantity == 100


def test_create_order_insufficient_inventory(client, session):
    """POST /orders/create rejects the order when inventory cannot satisfy it."""
    seed_inventory(
        session, customer_id=1, sku="tshirt", uom=None, quantity=10, location="loc-1"
    )

    resp = client.post(
        "/orders/create",
        data=json.dumps(
            {
                "customer_id": 1,
                "line_items": [{"sku": "tshirt", "quantity": 100}],
            }
        ),
        content_type="application/json",
    )

    # A client error in the 4xx range (e.g. 409 or 422) — exact code is your call.
    assert 400 <= resp.status_code < 500
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data['error'] == "Insufficient inventory for 'tshirt': requested 100, available 10"


def test_create_order_invalid_payload(client):
    """A payload missing required fields is rejected as a client error."""
    resp = client.post(
        "/orders/create",
        data=json.dumps({"line_items": [{"sku": "x", "quantity": 1}]}),
        content_type="application/json",
    )

    # A client error in the 4xx range (e.g. 400 or 422) — exact code is your call.
    assert 400 <= resp.status_code < 500
    data = resp.get_json()
    assert isinstance(data, dict)


def test_empty_line_items(client):
    """A payload missing required fields is rejected as a client error."""
    resp = client.post(
        "/orders/create",
        data=json.dumps({"customer_id": 1, "line_items": []}),
        content_type="application/json",
    )

    # A client error in the 4xx range (e.g. 400 or 422) — exact code is your call.
    assert resp.status_code == 422
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data['error'] == 'Line items must not be empty'


def test_line_item_quantity_must_be_positive_int(client):
    """A payload missing required fields is rejected as a client error."""
    resp = client.post(
        "/orders/create",
        data=json.dumps({"customer_id": 1, "line_items": [{"sku": "x", "quantity": -61}]}),
        content_type="application/json",
    )

    # A client error in the 4xx range (e.g. 400 or 422) — exact code is your call.
    assert resp.status_code == 422
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data['error'] == 'Quantity cannot be 0 or negative'


def test_line_item_quantity_must_not_be_zero(client):
    """A payload missing required fields is rejected as a client error."""
    resp = client.post(
        "/orders/create",
        data=json.dumps({"customer_id": 1, "line_items": [{"sku": "x", "quantity": 0}]}),
        content_type="application/json",
    )

    # A client error in the 4xx range (e.g. 400 or 422) — exact code is your call.
    assert resp.status_code == 422
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data['error'] == 'Quantity cannot be 0 or negative'


def test_empty_customer_id(client):
    """A payload missing required fields is rejected as a client error."""
    resp = client.post(
        "/orders/create",
        data=json.dumps({"line_items": []}),
        content_type="application/json",
    )

    # A client error in the 4xx range (e.g. 400 or 422) — exact code is your call.
    assert resp.status_code == 422
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data['error'] == 'Missing customer id'


def test_create_order_rolls_back_when_one_of_multiple_lines_fails(client, session):
    """
    Order has two line items. First can allocate, second cannot. Assert no order, no allocations, and no inventory
    deduction remains.

    line_items:
    - sku A quantity 10, enough stock
    - sku B quantity 999, not enough stock

    This is important because allocation mutates inventory before the whole order is known to be valid.
    """
    seed_inventory(
        session, customer_id=1, sku="tshirt", uom=None, quantity=100, location="loc-1"
    )
    seed_inventory(
        session, customer_id=1, sku="hat", uom=None, quantity=5, location="loc-2"
    )
    session.commit()

    resp = client.post(
        "/orders/create",
        data=json.dumps(
            {
                "customer_id": 1,
                "line_items": [
                    {"sku": "tshirt", "quantity": 40},
                    {"sku": "hat", "quantity": 10},
                ],
            }
        ),
        content_type="application/json",
    )

    assert 400 <= resp.status_code < 500
    assert session.query(Order).count() == 0
    assert session.query(Allocation).count() == 0

    tshirt_inventory = (
        session.query(ProductInventory)
        .filter_by(customer_id=1, sku="tshirt", location_identifier="loc-1")
        .one()
    )
    hat_inventory = (
        session.query(ProductInventory)
        .filter_by(customer_id=1, sku="hat", location_identifier="loc-2")
        .one()
    )
    assert tshirt_inventory.quantity == 100
    assert hat_inventory.quantity == 5
