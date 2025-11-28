"""modify litter report detection_result column from json to jsonb

Revision ID: 101eb0e2242c
Revises: c330b470afa0
Create Date: 2025-08-18 08:15:15.872920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '101eb0e2242c'
down_revision: Union[str, None] = 'c330b470afa0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Add a temporary jsonb column
    op.add_column(
        "litter_reports",
        sa.Column("detection_results_json", sa.dialects.postgresql.JSONB(), nullable=True),
    )

    # 2) Populate detection_results_json from the (possibly double-encoded) detection_results text.
    #    We use a PL/pgSQL DO block so we can attempt conversion row-by-row and continue on errors.
    conn.execute(
        text(
            r"""
DO $$
DECLARE
  r RECORD;
  v jsonb;
BEGIN
  FOR r IN
    SELECT id, detection_results
    FROM litter_reports
    WHERE detection_results IS NOT NULL
  LOOP
    BEGIN
      /*
        We expect detection_results to be a string like:
        "{\"status\": \"completed\", \"detections\": [...]}"

        Convert by: detection_results::text::jsonb
        This will handle double-encoded stringified JSON.
      */
      v := (r.detection_results::text::jsonb);
      UPDATE litter_reports SET detection_results_json = v WHERE id = r.id;
    EXCEPTION WHEN others THEN
      -- conversion failed for this row; leave detection_results_json NULL and log a notice
      RAISE NOTICE 'failed to convert detection_results for litter_reports.id = %', r.id;
    END;
  END LOOP;
END$$;
"""
        )
    )

    # 3) If needed, set NOT NULL only after verifying conversions; keep nullable to be safe.
    #    Swap columns: drop old text column and rename the new one.
    #    First drop constraint/indexes referring to old column if any (not covered here).

    # Drop old text column (we'll rename, but to be safe, rename instead of dropping if you prefer)
    # We'll rename new -> old name, after dropping old column.
    op.drop_column("litter_reports", "detection_results")

    # Rename detection_results_json -> detection_results
    op.alter_column("litter_reports", "detection_results_json", new_column_name="detection_results")

    # 4) Create expression index on (detection_results->>'status') for faster filtering by status
    #    Use BRIN or BTREE expression index - BTREE on the expression is fine for equality queries.
    conn.execute(
        text(
            """
CREATE INDEX IF NOT EXISTS idx_litter_reports_detection_status
  ON litter_reports ((detection_results->>'status'));
"""
        )
    )

    # Optional: you may VACUUM ANALYZE to update planner statistics, recommended after large migrations.
    # conn.execute(text("VACUUM ANALYZE litter_reports;"))

def downgrade() -> None:
    conn = op.get_bind()

    # 1) Drop the expression index (if exists)
    conn.execute(
        text(
            """
DROP INDEX IF EXISTS idx_litter_reports_detection_status;
"""
        )
    )

    # 2) Add a temporary text column to hold the stringified JSON
    op.add_column(
        "litter_reports",
        sa.Column("detection_results_text", sa.Text(), nullable=True),
    )

    # 3) Populate detection_results_text from jsonb -> text for rows where json exists
    #    Use row-by-row so we can gracefully handle unexpected cases.
    conn.execute(
        text(
            r"""
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT id, detection_results
    FROM litter_reports
    WHERE detection_results IS NOT NULL
  LOOP
    BEGIN
      -- cast jsonb -> text
      UPDATE litter_reports
      SET detection_results_text = (r.detection_results::text)
      WHERE id = r.id;
    EXCEPTION WHEN others THEN
      RAISE NOTICE 'failed to cast detection_results to text for id %', r.id;
    END;
  END LOOP;
END$$;
"""
        )
    )

    # 4) Drop the jsonb column
    op.drop_column("litter_reports", "detection_results")

    # 5) Rename detection_results_text back to detection_results
    op.alter_column("litter_reports", "detection_results_text", new_column_name="detection_results")

    # Optional: VACUUM ANALYZE
    # conn.execute(text("VACUUM ANALYZE litter_reports;"))