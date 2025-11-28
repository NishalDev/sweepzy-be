# worker_main.py
"""
Worker helper that:
 - lazily creates engine/session
 - imports model modules under the package 'api' (avoids duplicate imports)
 - calls configure_mappers() to ensure relationships are resolved
 - exposes CLI flags for manual testing
"""

import os
import sys
import logging
import argparse
import traceback
import importlib
import time
from pathlib import Path
from datetime import datetime, timedelta

# Quiet TensorFlow logs early, in case TF is imported later
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

logger = logging.getLogger("worker")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.handlers.clear()
logger.addHandler(handler)

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        try:
            from sqlalchemy import create_engine
            from config.settings import settings
        except Exception:
            logger.exception("❌ Failed to import create_engine or settings")
            raise
        _engine = create_engine(settings.DATABASE_URL)
    return _engine


def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        try:
            from sqlalchemy.orm import sessionmaker
        except Exception:
            logger.exception("❌ Failed to import sessionmaker")
            raise
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal


def _package_import_module(module_name: str) -> bool:
    """
    Import module using importlib.import_module(module_name).
    Return True if import succeeded, False otherwise.
    """
    try:
        if module_name in sys.modules:
            logger.debug(f"Module already loaded: {module_name}")
            return True
        importlib.import_module(module_name)
        logger.debug(f"✔ Imported: {module_name}")
        return True
    except Exception:
        logger.exception(f"✖ Failed to import module by package name: {module_name}")
        return False


def import_api_model_modules(api_dir: Path, debug: bool = False):
    """
    Discover likely model files under api_dir and import them using package names like:
      api.<subdirs>.<filename_without_py>
    This avoids importing the same file under a second synthetic module name.
    """
    if not api_dir.exists():
        logger.warning(f"api directory not found at {api_dir}")
        return

    # Ensure project root is on sys.path so 'import api.xxx' will work
    project_root = Path(__file__).parent.resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        logger.debug(f"Inserted project root into sys.path: {project_root}")

    candidates = []
    for p in api_dir.rglob("*.py"):
        name = p.name.lower()
        # choose patterns that likely contain model definitions
        if name.endswith("_model.py") or name.endswith("model.py") or name == "models.py":
            candidates.append(p)

    if debug:
        logger.debug("Model files discovered for import:")
        for c in candidates:
            logger.debug("  - " + str(c))

    successes = []
    failures = []
    for file_path in candidates:
        # Build dotted module name starting with 'api'
        try:
            rel = file_path.relative_to(api_dir)  # path inside api/
        except Exception:
            # shouldn't happen, but skip if it does
            logger.debug(f"Skipping non-api file: {file_path}")
            failures.append(file_path)
            continue

        dotted = "api." + ".".join(rel.with_suffix("").parts)
        ok = _package_import_module(dotted)
        (successes if ok else failures).append((file_path, dotted))

    if debug:
        logger.debug("Model import results:")
        for s in successes:
            if isinstance(s, tuple):
                logger.debug(f"  + {s[0]} as {s[1]}")
            else:
                logger.debug(f"  + {s}")
        for f in failures:
            if isinstance(f, tuple):
                logger.debug(f"  - {f[0]} as {f[1]}")
            else:
                logger.debug(f"  - {f}")


def _ensure_models_registered(debug: bool = False):
    """
    Import model files under api/ using package imports and then call configure_mappers().
    """
    base_dir = Path(__file__).parent.resolve()
    api_dir = base_dir / "api"
    import_api_model_modules(api_dir, debug=debug)

    try:
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        logger.debug("✔ configure_mappers() succeeded")
    except Exception:
        logger.error("❌ configure_mappers() failed — full traceback follows:")
        traceback.print_exc()


def update_upcoming_to_ongoing():
    _ensure_models_registered(debug=(logger.level == logging.DEBUG))

    try:
        from api.cleanup_events.cleanup_events_model import CleanupEvent
    except Exception:
        logger.exception("❌ Failed to import CleanupEvent model")
        return

    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        now = datetime.now()
        updated = (
            db.query(CleanupEvent)
            .filter(CleanupEvent.scheduled_date <= now)
            .filter(CleanupEvent.event_status == "upcoming")
            .update({"event_status": "ongoing"}, synchronize_session=False)
        )
        db.commit()
        logger.info(f"▶️ Updated {updated} event(s) to ongoing")
    except Exception:
        logger.exception("❌ Failed to update cleanup events")
    finally:
        try:
            db.close()
        except Exception:
            logger.exception("❌ Failed to close DB session in update_upcoming_to_ongoing")


def alert_users_before_event():
    _ensure_models_registered(debug=(logger.level == logging.DEBUG))

    try:
        from api.cleanup_events.cleanup_events_model import CleanupEvent
        from api.notifications.notifications_service import alert_event_starting
    except Exception:
        logger.exception("❌ Failed to import CleanupEvent or notifications service")
        return

    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        start_of_tomorrow = datetime(tomorrow.year, tomorrow.month, tomorrow.day)
        start_of_day_after = start_of_tomorrow + timedelta(days=1)

        events = (
            db.query(CleanupEvent)
            .filter(CleanupEvent.scheduled_date >= start_of_tomorrow)
            .filter(CleanupEvent.scheduled_date < start_of_day_after)
            .all()
        )

        if not events:
            logger.info("▶️ No events starting tomorrow (no alerts sent).")
        for event in events:
            try:
                logger.info(f"▶️ Alerting users for upcoming event {event.id}")
                alert_event_starting.send(sender=alert_users_before_event, event=event)
            except Exception:
                logger.exception(f"❌ Failed to alert users for event {getattr(event, 'id', 'unknown')}")
    except Exception:
        logger.exception("❌ Failed to send event start alerts")
    finally:
        try:
            db.close()
        except Exception:
            logger.exception("❌ Failed to close DB session in alert_users_before_event")


import time

def main(argv=None):
    parser = argparse.ArgumentParser(description="Worker helper (test/update/alert)")
    parser.add_argument("--interval", type=int, help="Interval in seconds between runs (loop mode)")
    parser.add_argument("--run-update", action="store_true", help="Run update_upcoming_to_ongoing() once")
    parser.add_argument("--run-alert", action="store_true", help="Run alert_users_before_event() once")
    parser.add_argument("--test", action="store_true", help="Run both jobs once")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args(argv)

    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # ✅ Loop mode if --interval is provided
    if args.interval:
        logger.info(f"▶️ Worker started in loop mode (interval={args.interval}s)")
        while True:
            try:
                update_upcoming_to_ongoing()
                alert_users_before_event()
            except Exception:
                logger.exception("❌ Worker loop error")
            time.sleep(args.interval)
        return

    # ✅ One-shot mode (default if no interval)
    if not (args.run_update or args.run_alert or args.test):
        logger.info("▶️ worker_main executed (no jobs run). Use --run-update, --run-alert, --test, or --interval.")
        return

    if args.test:
        logger.info("▶️ Running both jobs (test)")
        update_upcoming_to_ongoing()
        alert_users_before_event()
    else:
        if args.run_update:
            logger.info("▶️ Running update_upcoming_to_ongoing()")
            update_upcoming_to_ongoing()
        if args.run_alert:
            logger.info("▶️ Running alert_users_before_event()")
            alert_users_before_event()


if __name__ == "__main__":
    main()
