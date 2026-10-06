from flask import Flask, request, jsonify

from app.api.validations import validate_create_order
from app.domain.exceptions import OutOfStock
from app.infrastructure import db
from app.services.order_service import create_order

app = Flask(__name__)


# Note: Database schema initialization is handled once at container start
# via a prestart step, to avoid concurrent DDL with multiple workers.


@app.post("/orders/create")
def create_order_endpoint():
    """
    Payload:
    {
      "customer_id": 1,
      "line_items": [
        {"sku": "tshirt-blue", "quantity": 2500},
        ...
      ]
    }
    Returns: {"order_id": <int>}
    """
    payload = request.get_json(silent=True) or {}
    customer_id = payload.get("customer_id")
    line_items = payload.get("line_items", [])
    error = validate_create_order(payload)
    if error:
        return jsonify({'error': error}), 422

    session = db.get_session()
    try:
        order = create_order(session, customer_id, line_items)
    except OutOfStock as e:
        session.rollback()
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400

    session.commit()
    return jsonify({"order_id": order.id}), 201


@app.get("/health")
def health():
    return jsonify({"ok": True})
