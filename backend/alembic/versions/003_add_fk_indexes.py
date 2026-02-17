"""Add FK indexes for performance

Revision ID: 003
Revises: 002
Create Date: 2026-02-17 12:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_operations_receipt_id', 'operations', ['receipt_id'])
    op.create_index('ix_operations_employee_id', 'operations', ['employee_id'])
    op.create_index('ix_polishing_details_polisher_id', 'polishing_details', ['polisher_id'])
    op.create_index('ix_history_events_receipt_id', 'history_events', ['receipt_id'])
    op.create_index('ix_notifications_receipt_id', 'notifications', ['receipt_id'])
    op.create_index('ix_returns_receipt_id', 'returns', ['receipt_id'])


def downgrade() -> None:
    op.drop_index('ix_returns_receipt_id', table_name='returns')
    op.drop_index('ix_notifications_receipt_id', table_name='notifications')
    op.drop_index('ix_history_events_receipt_id', table_name='history_events')
    op.drop_index('ix_polishing_details_polisher_id', table_name='polishing_details')
    op.drop_index('ix_operations_employee_id', table_name='operations')
    op.drop_index('ix_operations_receipt_id', table_name='operations')
