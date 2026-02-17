"""
API endpoints для уведомлений.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_api_key
from app.schemas.notification import NotificationResponse, NotificationListResponse
from app.services.notification_service import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/pending", response_model=NotificationListResponse)
def get_pending_notifications(db: Session = Depends(get_db)):
    """Получить список неотправленных уведомлений, время которых наступило."""
    service = NotificationService(db)
    notifications = service.get_pending()

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=len(notifications),
    )


@router.post("/{notification_id}/mark-sent", response_model=NotificationResponse)
def mark_notification_sent(notification_id: int, db: Session = Depends(get_db)):
    """Отметить уведомление как отправленное."""
    service = NotificationService(db)
    service.mark_sent(notification_id)

    from app.models.notification import Notification
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    return NotificationResponse.model_validate(notif)
