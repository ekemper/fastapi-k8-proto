"""update enrich job type to singular

Revision ID: b19d5995b29c
Revises: 0a2b4deb976f
Create Date: 2025-05-30 23:xx:xx.xxxxxx

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b19d5995b29c'
down_revision: Union[str, None] = '0a2b4deb976f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new ENRICH_LEAD enum value and commit it
    connection = op.get_bind()
    connection.execute(sa.text("ALTER TYPE jobtype ADD VALUE 'ENRICH_LEAD'"))
    connection.commit()
    
    # Now update existing data: change ENRICH_LEADS to ENRICH_LEAD
    connection.execute(sa.text("UPDATE jobs SET job_type = 'ENRICH_LEAD' WHERE job_type = 'ENRICH_LEADS'"))
    
    # Note: We cannot easily remove enum values in PostgreSQL without recreating the enum
    # The old ENRICH_LEADS value will remain in the enum but won't be used
    # This is the safest approach for production systems


def downgrade() -> None:
    # Update data back to ENRICH_LEADS
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE jobs SET job_type = 'ENRICH_LEADS' WHERE job_type = 'ENRICH_LEAD'"))
    
    # Note: We cannot remove the ENRICH_LEAD enum value without recreating the enum
    # The downgrade restores the data but both enum values will exist
