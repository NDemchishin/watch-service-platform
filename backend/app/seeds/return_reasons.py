"""
Сид причин возвратов.
"""
from sqlalchemy.orm import Session

from app.models.return_ import ReturnReason


RETURN_REASONS = [
    {"code": "dirt_inside", "name": "Грязь внутри", "affects": "assembly"},
    {"code": "dirt_outside", "name": "Грязь снаружи", "affects": "assembly"},
    {"code": "mechanism_defect", "name": "Дефект механизма", "affects": "mechanism"},
    {"code": "no_numbers", "name": "Не выписал номера", "affects": "assembly"},
    {"code": "wrong_assembly", "name": "Неправильная сборка", "affects": "assembly"},
    {"code": "polishing", "name": "Полировка", "affects": "polishing"},
]


def seed_return_reasons(db: Session):
    """Заполняет таблицу причин возвратов."""
    for reason in RETURN_REASONS:
        exists = db.query(ReturnReason).filter_by(code=reason["code"]).first()
        if not exists:
            db.add(ReturnReason(**reason))
    db.commit()
