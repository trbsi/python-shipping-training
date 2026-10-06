class OutOfStock(Exception):
    """Raised when inventory cannot satisfy the requested quantity."""

    def __init__(self, sku: str, requested: int, available: int):
        self.sku = sku
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient inventory for '{sku}': requested {requested}, available {available}"
        )
