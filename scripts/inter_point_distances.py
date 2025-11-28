from sqlalchemy import create_engine, text
from shapely import wkb
from itertools import combinations

# 1) Connect to your DB
engine = create_engine(
    "" # your database URL here, e.g. "postgresql+psycopg2://user:password@localhost/dbname"
)

# 2) The five report UUIDs you want to inspect
REPORT_UUIDS = [
    ""  # put your report UUIDs here as strings, e.g. "123e4567-e89b-12d3-a456-426614174000"
]

with engine.connect() as conn:
    sql = text("""
        SELECT
          id,
          ST_AsEWKB(ST_Transform(geom, 3857)) AS geom_3857
        FROM litter_reports
        WHERE id IN :uuids
    """)
    # pass a tuple for an IN-list
    rows = conn.execute(sql, {"uuids": tuple(REPORT_UUIDS)}).fetchall()

# Load into Shapely and compute distances
points = [(row.id, wkb.loads(bytes(row.geom_3857))) for row in rows]

print("Pairwise distances (meters):")
for (id1, p1), (id2, p2) in combinations(points, 2):
    d = p1.distance(p2)
    note = "  <-- exceeds 500 m" if d > 500 else ""
    print(f"  {id1} ↔ {id2}: {d:.1f} m{note}")
