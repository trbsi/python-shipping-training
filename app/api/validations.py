def validate_create_order(data: dict) -> str | None:
    if not data:
        return "Missing the body"

    if "customer_id" not in data:
        return "Missing customer id"

    if not isinstance(data['customer_id'], int):
        return "Customer id must be integer"

    if not 'line_items' in data:
        return "Line items are missing"

    if not isinstance(data['line_items'], list) or len(data['line_items']) == 0:
        return "Line items must not be empty"

    for i, line_item in enumerate(data['line_items']):
        if "sku" not in line_item:
            return f"line_items[{i}].sku is required"

        if "quantity" not in line_item:
            return f"line_items[{i}].quantity is required"

        if not isinstance(line_item["quantity"], int) or line_item["quantity"] <= 0:
            return "Quantity cannot be 0 or negative"

    return None
