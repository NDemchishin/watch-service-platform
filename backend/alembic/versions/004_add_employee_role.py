"""Add role column to employees

Revision ID: 004
Revises: 003
Create Date: 2026-02-17 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем колонку с дефолтом для существующих записей
    op.add_column('employees', sa.Column('role', sa.String(), nullable=False, server_default='master'))
    # Убираем server_default после заполнения — дефолт будет на уровне ORM
    op.alter_column('employees', 'role', server_default=None)


def downgrade() -> None:
    op.drop_column('employees', 'role')
