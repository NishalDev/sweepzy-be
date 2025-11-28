"""Quick DB inspector for detection data used by export_to_coco.

Run from root folder:
  python scripts/inspect_detections.py

Prints counts and sample rows from litter_detections and litter_reports.
"""
from pathlib import Path
import sys
import json

_pkg_root = Path(__file__).resolve().parents[1]
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from config.database import engine
from sqlalchemy import text


def pretty(o):
    try:
        return json.dumps(o, indent=2, default=str)
    except Exception:
        return repr(o)


def run():
    conn = engine.connect()
    try:
        q1 = text('SELECT count(*) FROM litter_detections')
        c1 = conn.execute(q1).scalar()
        print(f'litter_detections count: {c1}')

        q2 = text('SELECT id::text, litter_report_id::text, total_litter_count, bounding_boxes, detected_objects FROM litter_detections ORDER BY created_at DESC LIMIT 5')
        rows = conn.execute(q2).mappings().all()
        print('\nRecent litter_detections (up to 5):')
        for i, r in enumerate(rows, 1):
            print('--- row', i)
            print('id:', r.get('id') or r.get('id') or r.get('litter_report_id'))
            print('litter_report_id:', r.get('litter_report_id'))
            print('total_litter_count:', r.get('total_litter_count'))
            print('bounding_boxes type:', type(r.get('bounding_boxes')))
            print('bounding_boxes:', pretty(r.get('bounding_boxes')))
            print('detected_objects type:', type(r.get('detected_objects')))
            print('detected_objects:', pretty(r.get('detected_objects')))

        q3 = text('SELECT count(*) FROM litter_reports WHERE detection_results IS NOT NULL')
        c2 = conn.execute(q3).scalar()
        print(f'\nlitter_reports with detection_results: {c2}')

        q4 = text('SELECT id::text, detection_results FROM litter_reports WHERE detection_results IS NOT NULL ORDER BY updated_at DESC LIMIT 5')
        reps = conn.execute(q4).mappings().all()
        print('\nRecent litter_reports with detection_results (up to 5):')
        for i, r in enumerate(reps, 1):
            print('--- report', i)
            print('id:', r.get('id'))
            dr = r.get('detection_results')
            print('type:', type(dr))
            print('value:', pretty(dr))

    finally:
        conn.close()


if __name__ == '__main__':
    run()
