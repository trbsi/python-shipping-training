from dataclasses import dataclass


@dataclass
class InventoryItem:
    id: int | None
    sku: str
    uom: str | None
    quantity: int
    location_identifier: str
