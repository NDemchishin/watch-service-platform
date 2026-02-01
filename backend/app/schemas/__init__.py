"""
Pydantic схемы для валидации данных.
"""
from app.schemas.employee import (
    EmployeeBase,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeListResponse,
)
from app.schemas.receipt import (
    ReceiptBase,
    ReceiptCreate,
    ReceiptUpdate,
    ReceiptResponse,
    ReceiptListResponse,
    ReceiptWithHistoryResponse,
)
from app.schemas.operation import (
    OperationTypeBase,
    OperationTypeResponse,
    OperationTypeListResponse,
    OperationBase,
    OperationCreate,
    OperationResponse,
    OperationListResponse,
)
from app.schemas.polishing import (
    PolishingDetailsBase,
    PolishingDetailsCreate,
    PolishingDetailsUpdate,
    PolishingDetailsResponse,
    PolishingDetailsListResponse,
    PolishingStatsResponse,
)
from app.schemas.return_ import (
    ReturnReasonBase,
    ReturnReasonResponse,
    ReturnReasonListResponse,
    ReturnReasonLinkCreate,
    ReturnReasonLinkResponse,
    ReturnBase,
    ReturnCreate,
    ReturnResponse,
    ReturnListResponse,
)
from app.schemas.history import (
    HistoryEventBase,
    HistoryEventCreate,
    HistoryEventResponse,
    HistoryEventListResponse,
)

__all__ = [
    # Employee
    "EmployeeBase",
    "EmployeeCreate",
    "EmployeeUpdate",
    "EmployeeResponse",
    "EmployeeListResponse",
    # Receipt
    "ReceiptBase",
    "ReceiptCreate",
    "ReceiptUpdate",
    "ReceiptResponse",
    "ReceiptListResponse",
    "ReceiptWithHistoryResponse",
    # Operation
    "OperationTypeBase",
    "OperationTypeResponse",
    "OperationTypeListResponse",
    "OperationBase",
    "OperationCreate",
    "OperationResponse",
    "OperationListResponse",
    # Polishing
    "PolishingDetailsBase",
    "PolishingDetailsCreate",
    "PolishingDetailsUpdate",
    "PolishingDetailsResponse",
    "PolishingDetailsListResponse",
    "PolishingStatsResponse",
    # Return
    "ReturnReasonBase",
    "ReturnReasonResponse",
    "ReturnReasonListResponse",
    "ReturnReasonLinkCreate",
    "ReturnReasonLinkResponse",
    "ReturnBase",
    "ReturnCreate",
    "ReturnResponse",
    "ReturnListResponse",
    # History
    "HistoryEventBase",
    "HistoryEventCreate",
    "HistoryEventResponse",
    "HistoryEventListResponse",
]
