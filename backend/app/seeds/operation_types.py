"""
Сид типов операций.
"""
from sqlalchemy.orm import Session

from app.models.operation import OperationType


OPERATION_TYPES = [
    {"code": "assembly", "name": "Сборка"},
    {"code": "mechanism", "name": "Ремонт механизма"},
    {"code": "polishing", "name": "Полировка"},
]


def seed_operation_types(db: Session):
    """Заполняет таблицу типов операций."""
    for op_type in OPERATION_TYPES:
        exists = db.query(OperationType).filter_by(code=op_type["code"]).first()
        if not exists:
            db.add(OperationType(**op_type))
    db.commit()
