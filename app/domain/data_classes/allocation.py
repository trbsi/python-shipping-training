from dataclasses import dataclass


@dataclass
class Allocation:
    inventory_id: int | None
    sku: str
    location_identifier: str
    quantity: int
    uom: str | None
