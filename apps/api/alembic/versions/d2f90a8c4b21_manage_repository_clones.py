"""manage repository clones

Revision ID: d2f90a8c4b21
Revises: b4e21d7c91aa
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d2f90a8c4b21"
down_revision: Union[str, Sequence[str], None] = "b4e21d7c91aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("repositories") as batch_op:
        batch_op.drop_constraint("uq_repository_project_path", type_="unique")
        batch_op.drop_column("local_path")
        batch_op.add_column(sa.Column("managed_path", sa.String(length=1000), nullable=True))
        batch_op.create_unique_constraint("uq_repository_project_remote", ["project_id", "remote_url"])


def downgrade() -> None:
    with op.batch_alter_table("repositories") as batch_op:
        batch_op.drop_constraint("uq_repository_project_remote", type_="unique")
        batch_op.drop_column("managed_path")
        batch_op.add_column(sa.Column("local_path", sa.String(length=1000), nullable=False, server_default=""))
        batch_op.create_unique_constraint("uq_repository_project_path", ["project_id", "local_path"])
