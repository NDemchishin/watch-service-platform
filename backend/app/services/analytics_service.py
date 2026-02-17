"""
Сервис аналитики — агрегационные запросы для Sprint 6.
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case

from app.models.operation import Operation, OperationType
from app.models.return_ import Return, ReturnReason, ReturnReasonLink
from app.models.polishing import PolishingDetails
from app.models.employee import Employee
from app.core.utils import now_moscow


class AnalyticsService:
    """Сервис аналитики."""

    def __init__(self, db: Session):
        self.db = db

    # ---- helpers ----

    def _period_start(self, period: str) -> Optional[datetime]:
        """Возвращает начало периода или None для 'all'."""
        if period == "all":
            return None
        now = now_moscow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "day":
            return today_start
        if period == "week":
            return today_start - timedelta(days=today_start.weekday())
        if period == "month":
            return today_start.replace(day=1)
        return None

    # ---- Issue #28: качество сборки ----

    def assembly_quality(
        self, period: str = "all", employee_id: Optional[int] = None
    ) -> dict:
        """
        Качество сборки по сотрудникам.
        Учитываются только возвраты с причинами affects='assembly'.
        """
        period_start = self._period_start(period)

        # Получаем ID типа операции "assembly"
        assembly_type = (
            self.db.query(OperationType)
            .filter(OperationType.code == "assembly")
            .first()
        )
        if not assembly_type:
            return {"period": period, "employees": []}

        # Базовый фильтр по операциям сборки
        op_filters = [Operation.operation_type_id == assembly_type.id]
        if period_start:
            op_filters.append(Operation.created_at >= period_start)
        if employee_id:
            op_filters.append(Operation.employee_id == employee_id)

        # Количество сборок по сотрудникам
        ops_q = (
            self.db.query(
                Operation.employee_id,
                Employee.name,
                func.count(Operation.id).label("total"),
            )
            .join(Employee, Operation.employee_id == Employee.id)
            .filter(*op_filters)
            .group_by(Operation.employee_id, Employee.name)
            .all()
        )

        # Возвраты по причинам сборки (affects='assembly')
        ret_filters = [ReturnReason.affects == "assembly"]
        if period_start:
            ret_filters.append(Return.created_at >= period_start)

        # Считаем возвраты по сотрудникам операций сборки.
        # Связь: Return -> receipt_id -> Operation(assembly) -> employee_id
        ret_q = (
            self.db.query(
                Operation.employee_id,
                func.count(func.distinct(Return.id)).label("returns"),
            )
            .select_from(Return)
            .join(ReturnReasonLink, ReturnReasonLink.return_id == Return.id)
            .join(ReturnReason, ReturnReasonLink.reason_id == ReturnReason.id)
            .join(
                Operation,
                and_(
                    Operation.receipt_id == Return.receipt_id,
                    Operation.operation_type_id == assembly_type.id,
                ),
            )
            .filter(*ret_filters)
        )
        if employee_id:
            ret_q = ret_q.filter(Operation.employee_id == employee_id)
        ret_q = ret_q.group_by(Operation.employee_id).all()

        returns_map = {row.employee_id: row.returns for row in ret_q}

        employees = []
        for row in ops_q:
            total = row.total
            returns = returns_map.get(row.employee_id, 0)
            quality = round((1 - returns / total) * 100, 1) if total > 0 else 100.0
            employees.append(
                {
                    "employee_id": row.employee_id,
                    "employee_name": row.name,
                    "total_operations": total,
                    "total_returns": returns,
                    "quality_percent": quality,
                }
            )

        return {"period": period, "employees": employees}

    # ---- Issue #29: качество механизма ----

    def mechanism_quality(
        self, period: str = "all", employee_id: Optional[int] = None
    ) -> dict:
        """
        Качество ремонта механизма по сотрудникам.
        Учитываются только возвраты с причиной affects='mechanism'.
        """
        period_start = self._period_start(period)

        mechanism_type = (
            self.db.query(OperationType)
            .filter(OperationType.code == "mechanism")
            .first()
        )
        if not mechanism_type:
            return {"period": period, "employees": []}

        op_filters = [Operation.operation_type_id == mechanism_type.id]
        if period_start:
            op_filters.append(Operation.created_at >= period_start)
        if employee_id:
            op_filters.append(Operation.employee_id == employee_id)

        ops_q = (
            self.db.query(
                Operation.employee_id,
                Employee.name,
                func.count(Operation.id).label("total"),
            )
            .join(Employee, Operation.employee_id == Employee.id)
            .filter(*op_filters)
            .group_by(Operation.employee_id, Employee.name)
            .all()
        )

        ret_filters = [ReturnReason.affects == "mechanism"]
        if period_start:
            ret_filters.append(Return.created_at >= period_start)

        ret_q = (
            self.db.query(
                Operation.employee_id,
                func.count(func.distinct(Return.id)).label("returns"),
            )
            .select_from(Return)
            .join(ReturnReasonLink, ReturnReasonLink.return_id == Return.id)
            .join(ReturnReason, ReturnReasonLink.reason_id == ReturnReason.id)
            .join(
                Operation,
                and_(
                    Operation.receipt_id == Return.receipt_id,
                    Operation.operation_type_id == mechanism_type.id,
                ),
            )
            .filter(*ret_filters)
        )
        if employee_id:
            ret_q = ret_q.filter(Operation.employee_id == employee_id)
        ret_q = ret_q.group_by(Operation.employee_id).all()

        returns_map = {row.employee_id: row.returns for row in ret_q}

        employees = []
        for row in ops_q:
            total = row.total
            returns = returns_map.get(row.employee_id, 0)
            quality = round((1 - returns / total) * 100, 1) if total > 0 else 100.0
            employees.append(
                {
                    "employee_id": row.employee_id,
                    "employee_name": row.name,
                    "total_operations": total,
                    "total_returns": returns,
                    "quality_percent": quality,
                }
            )

        return {"period": period, "employees": employees}

    # ---- Issue #30: качество полировки ----

    def polishing_quality(
        self, period: str = "all", polisher_id: Optional[int] = None
    ) -> dict:
        """
        Качество полировки по полировщикам.
        Учитываются только возвраты с причиной affects='polishing'
        и виновный полировщик (guilty_employee из ReturnReasonLink).
        """
        period_start = self._period_start(period)

        # Количество завершённых полировок по полировщикам
        pol_filters = [PolishingDetails.returned_at.isnot(None)]
        if period_start:
            pol_filters.append(PolishingDetails.sent_at >= period_start)
        if polisher_id:
            pol_filters.append(PolishingDetails.polisher_id == polisher_id)

        pol_q = (
            self.db.query(
                PolishingDetails.polisher_id,
                Employee.name,
                func.count(PolishingDetails.receipt_id).label("total"),
            )
            .join(Employee, PolishingDetails.polisher_id == Employee.id)
            .filter(*pol_filters)
            .group_by(PolishingDetails.polisher_id, Employee.name)
            .all()
        )

        # Возвраты по полировке — учитываем guilty_employee_id из ReturnReasonLink
        ret_filters = [ReturnReason.affects == "polishing"]
        if period_start:
            ret_filters.append(Return.created_at >= period_start)

        ret_q = (
            self.db.query(
                ReturnReasonLink.guilty_employee_id,
                func.count(func.distinct(Return.id)).label("returns"),
            )
            .select_from(Return)
            .join(ReturnReasonLink, ReturnReasonLink.return_id == Return.id)
            .join(ReturnReason, ReturnReasonLink.reason_id == ReturnReason.id)
            .filter(*ret_filters)
            .filter(ReturnReasonLink.guilty_employee_id.isnot(None))
        )
        if polisher_id:
            ret_q = ret_q.filter(
                ReturnReasonLink.guilty_employee_id == polisher_id
            )
        ret_q = ret_q.group_by(ReturnReasonLink.guilty_employee_id).all()

        returns_map = {row.guilty_employee_id: row.returns for row in ret_q}

        polishers = []
        for row in pol_q:
            total = row.total
            returns = returns_map.get(row.polisher_id, 0)
            quality = round((1 - returns / total) * 100, 1) if total > 0 else 100.0
            polishers.append(
                {
                    "employee_id": row.polisher_id,
                    "employee_name": row.name,
                    "total_polished": total,
                    "total_returns": returns,
                    "quality_percent": quality,
                }
            )

        return {"period": period, "polishers": polishers}

    # ---- Issue #31: загрузка полировщиков ----

    def polishing_workload(self) -> dict:
        """
        Текущая загрузка полировщиков:
        - в работе / завершено
        - breakdown: сложные / простые, с браслетом / без
        - среднее время полировки
        """
        # Все полировки, сгруппированные по полировщику
        polishers_q = (
            self.db.query(
                PolishingDetails.polisher_id,
                Employee.name,
                func.count(PolishingDetails.receipt_id).label("total"),
                func.sum(
                    case((PolishingDetails.returned_at.is_(None), 1), else_=0)
                ).label("in_progress"),
                func.sum(
                    case((PolishingDetails.returned_at.isnot(None), 1), else_=0)
                ).label("completed"),
                func.sum(
                    case((PolishingDetails.difficult == True, 1), else_=0)
                ).label("difficult_count"),
                func.sum(
                    case((PolishingDetails.difficult == False, 1), else_=0)
                ).label("simple_count"),
                func.sum(
                    case((PolishingDetails.bracelet == True, 1), else_=0)
                ).label("with_bracelet"),
                func.sum(
                    case((PolishingDetails.bracelet == False, 1), else_=0)
                ).label("without_bracelet"),
            )
            .join(Employee, PolishingDetails.polisher_id == Employee.id)
            .group_by(PolishingDetails.polisher_id, Employee.name)
            .all()
        )

        polishers = []
        for row in polishers_q:
            # Вычисляем часы для завершённых полировок
            hours_q = (
                self.db.query(PolishingDetails)
                .filter(
                    PolishingDetails.polisher_id == row.polisher_id,
                    PolishingDetails.returned_at.isnot(None),
                )
                .all()
            )
            total_hours = 0.0
            for p in hours_q:
                delta = p.returned_at - p.sent_at
                total_hours += delta.total_seconds() / 3600

            completed = int(row.completed or 0)
            avg_hours = round(total_hours / completed, 2) if completed > 0 else None

            # Для незавершённых — считаем часы от sent_at до now
            in_progress_q = (
                self.db.query(PolishingDetails)
                .filter(
                    PolishingDetails.polisher_id == row.polisher_id,
                    PolishingDetails.returned_at.is_(None),
                )
                .all()
            )
            in_progress_hours = 0.0
            now = now_moscow()
            for p in in_progress_q:
                delta = now - p.sent_at
                in_progress_hours += delta.total_seconds() / 3600

            polishers.append(
                {
                    "employee_id": row.polisher_id,
                    "employee_name": row.name,
                    "in_progress": int(row.in_progress or 0),
                    "completed": completed,
                    "total_hours": round(total_hours + in_progress_hours, 2),
                    "simple_count": int(row.simple_count or 0),
                    "difficult_count": int(row.difficult_count or 0),
                    "with_bracelet": int(row.with_bracelet or 0),
                    "without_bracelet": int(row.without_bracelet or 0),
                    "avg_hours": avg_hours,
                }
            )

        return {"polishers": polishers}

    # ---- Issue #32: производительность за период ----

    def performance(
        self, period: str = "all", employee_id: Optional[int] = None
    ) -> dict:
        """Операции за период по сотрудникам, с группировкой по типу."""
        period_start = self._period_start(period)

        filters = []
        if period_start:
            filters.append(Operation.created_at >= period_start)
        if employee_id:
            filters.append(Operation.employee_id == employee_id)

        rows = (
            self.db.query(
                Operation.employee_id,
                Employee.name,
                OperationType.code,
                func.count(Operation.id).label("cnt"),
            )
            .join(Employee, Operation.employee_id == Employee.id)
            .join(OperationType, Operation.operation_type_id == OperationType.id)
            .filter(*filters)
            .group_by(Operation.employee_id, Employee.name, OperationType.code)
            .all()
        )

        emp_map: dict[int, dict] = {}
        total_assembly = 0
        total_mechanism = 0
        total_polishing = 0

        for row in rows:
            eid = row.employee_id
            if eid not in emp_map:
                emp_map[eid] = {
                    "employee_id": eid,
                    "employee_name": row.name,
                    "assembly_count": 0,
                    "mechanism_count": 0,
                    "polishing_count": 0,
                    "total_count": 0,
                }
            cnt = row.cnt
            if row.code == "assembly":
                emp_map[eid]["assembly_count"] += cnt
                total_assembly += cnt
            elif row.code == "mechanism":
                emp_map[eid]["mechanism_count"] += cnt
                total_mechanism += cnt
            elif row.code == "polishing":
                emp_map[eid]["polishing_count"] += cnt
                total_polishing += cnt
            emp_map[eid]["total_count"] += cnt

        return {
            "period": period,
            "employees": list(emp_map.values()),
            "total_assembly": total_assembly,
            "total_mechanism": total_mechanism,
            "total_polishing": total_polishing,
            "total_operations": total_assembly + total_mechanism + total_polishing,
        }

    # ---- Issue #32: сводка возвратов ----

    def returns_summary(
        self, period: str = "all"
    ) -> dict:
        """Возвраты за период по причинам + топ сотрудников по возвратам."""
        period_start = self._period_start(period)

        base_filters = []
        if period_start:
            base_filters.append(Return.created_at >= period_start)

        # Всего возвратов
        total = (
            self.db.query(func.count(Return.id))
            .filter(*base_filters)
            .scalar()
        ) or 0

        # По причинам
        reason_q = (
            self.db.query(
                ReturnReason.code,
                ReturnReason.name,
                func.count(ReturnReasonLink.id).label("cnt"),
            )
            .select_from(ReturnReasonLink)
            .join(ReturnReason, ReturnReasonLink.reason_id == ReturnReason.id)
            .join(Return, ReturnReasonLink.return_id == Return.id)
            .filter(*base_filters)
            .group_by(ReturnReason.code, ReturnReason.name)
            .order_by(func.count(ReturnReasonLink.id).desc())
            .all()
        )

        by_reason = [
            {"reason_code": r.code, "reason_name": r.name, "count": r.cnt}
            for r in reason_q
        ]

        # Топ сотрудников по возвратам (по количеству возвратов на их операции)
        top_q = (
            self.db.query(
                Operation.employee_id,
                Employee.name,
                func.count(func.distinct(Return.id)).label("cnt"),
            )
            .select_from(Return)
            .join(Operation, Operation.receipt_id == Return.receipt_id)
            .join(Employee, Operation.employee_id == Employee.id)
            .filter(*base_filters)
            .group_by(Operation.employee_id, Employee.name)
            .order_by(func.count(func.distinct(Return.id)).desc())
            .limit(10)
            .all()
        )

        top_employees = [
            {
                "employee_id": r.employee_id,
                "employee_name": r.name,
                "total_returns": r.cnt,
            }
            for r in top_q
        ]

        return {
            "period": period,
            "total_returns": total,
            "by_reason": by_reason,
            "top_employees": top_employees,
        }
