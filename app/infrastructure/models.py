from datetime import datetime, UTC

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now(UTC), nullable=False)
    line_items = relationship(
        "OrderLineItem", back_populates="order", cascade="all, delete-orphan"
    )
    allocations = relationship(
        "Allocation", back_populates="order", cascade="all, delete-orphan"
    )


class OrderLineItem(Base):
    __tablename__ = "order_line_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    sku = Column(String(128), nullable=False)
    quantity = Column(Integer, nullable=False)  # in eaches
    order = relationship("Order", back_populates="line_items")
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_line_qty_nonneg"),
        Index("ix_oli_order_sku", "order_id", "sku"),
    )


class ProductInventory(Base):
    __tablename__ = "product_inventory"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, nullable=False)
    sku = Column(String(128), nullable=False)
    # uom can be 'pallet', 'case', or NULL meaning eaches
    uom = Column(String(16), nullable=True)
    quantity = Column(
        Integer, nullable=False
    )  # quantity in the given uom (or eaches if uom is NULL)
    location_identifier = Column(String(128), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_inventory_qty_nonneg"),
        UniqueConstraint(
            "customer_id",
            "sku",
            "uom",
            "location_identifier",
            name="uq_inv_unique_slot",
        ),
        Index("ix_inv_customer_sku", "customer_id", "sku"),
    )


class UomProduct(Base):
    __tablename__ = "uom_products"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, nullable=False)
    sku = Column(String(128), nullable=False)
    uom = Column(String(16), nullable=False)  # 'pallet' or 'case'
    ea_qty = Column(Integer, nullable=False)  # eaches per one 'uom'
    __table_args__ = (
        UniqueConstraint("customer_id", "sku", "uom", name="uq_uom_map"),
        CheckConstraint("ea_qty > 0", name="ck_ea_qty_positive"),
        Index("ix_uom_customer_sku", "customer_id", "sku"),
    )


class Allocation(Base):
    __tablename__ = "allocations"
    id = Column(Integer, primary_key=True)
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )

    customer_id = Column(Integer, nullable=False)
    sku = Column(String(128), nullable=False)
    location_identifier = Column(String(128), nullable=False)
    quantity = Column(Integer, nullable=False)  # store allocated in eaches
    uom = Column(
        String(16), nullable=True
    )  # uom of the source slot ('pallet'/'case'/NULL)

    order = relationship("Order", back_populates="allocations")
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_alloc_qty_positive"),
        Index("ix_alloc_order", "order_id"),
    )
