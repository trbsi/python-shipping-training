from sqlalchemy.orm import Session

from app.infrastructure.models import ProductInventory, UomProduct


def get_product_inventory_for_sku_and_customer(session: Session, customer_id: int, skus: list[str]) -> list[ProductInventory]:
    return (
        session.query(ProductInventory)
        .filter(ProductInventory.customer_id == customer_id, ProductInventory.sku.in_(skus))
        .all()
    )


def get_uom_products_by_sku_and_customer(session: Session, customer_id: int, skus: list[str]) -> list[UomProduct]:
    return (
        session.query(UomProduct)
        .filter(UomProduct.customer_id == customer_id, UomProduct.sku.in_(skus))
        .all()
    )
