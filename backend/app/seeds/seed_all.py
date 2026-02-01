"""
Запуск всех сидов.
"""
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.seeds.operation_types import seed_operation_types
from app.seeds.return_reasons import seed_return_reasons


def run_all_seeds():
    """Запускает все сиды."""
    db = SessionLocal()
    try:
        seed_operation_types(db)
        seed_return_reasons(db)
        print("All seeds completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    run_all_seeds()
