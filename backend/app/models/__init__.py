"""
Модели SQLAlchemy — импортируем все для корректной регистрации relationship.
"""
from app.models.employee import Employee  # noqa: F401
from app.models.receipt import Receipt  # noqa: F401
from app.models.operation import Operation, OperationType  # noqa: F401
from app.models.polishing import PolishingDetails  # noqa: F401
from app.models.return_ import Return, ReturnReason, ReturnReasonLink  # noqa: F401
from app.models.history import HistoryEvent  # noqa: F401
from app.models.notification import Notification  # noqa: F401
