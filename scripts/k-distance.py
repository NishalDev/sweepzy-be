#!/usr/bin/env python
# scripts/k_distance.py

import os
import sys
import psycopg2
import numpy as np
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors

# ─── Configuration ─────────────────────────────────────────────────────────────

# Pull from env vars or fallback to defaults
DB_NAME = os.getenv("PGDATABASE", "") # your database name here"
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASS = os.getenv("PGPASSWORD", "") # your database password here"
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = os.getenv("PGPORT", "5432")

MINPTS = 3  # same as the DBSCAN minpts you use

# ─── Fetch & project points ────────────────────────────────────────────────────

def fetch_points():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS,
            host=DB_HOST, port=DB_PORT
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT ST_X(geom3857), ST_Y(geom3857)
              FROM (
                    SELECT ST_Transform(geom, 3857) AS geom3857
                      FROM litter_reports
                     WHERE group_id IS NULL
                ) AS sub
        """)
        rows = cur.fetchall()
        conn.close()
        return np.array(rows, dtype=float)
    except Exception as e:
        print(f"Database error: {e}")
        sys.exit(1)

# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    coords = fetch_points()
    n = coords.shape[0]

    if n < MINPTS:
        print(f"Only {n} point(s) available; need at least {MINPTS} for a k-distance plot.")
        return

    k = min(MINPTS, n)
    nbrs = NearestNeighbors(n_neighbors=k).fit(coords)
    distances, _ = nbrs.kneighbors(coords)
    k_distances = np.sort(distances[:, -1])  # k-distance

    plt.figure(figsize=(8, 4))
    plt.plot(k_distances, marker='.', linestyle='-')
    plt.ylabel(f"Distance to {k}th nearest neighbor (meters)")
    plt.xlabel("Points sorted by distance")
    plt.title("k‑Distance Plot (for ε selection)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
