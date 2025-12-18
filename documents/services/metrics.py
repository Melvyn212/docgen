import time
from typing import Optional

import redis
from django.conf import settings


def _client():
    """
    Reuse a single Redis client. Default to CELERY_BROKER_URL if it is Redis, otherwise fallback to localhost.
    """
    url = getattr(settings, "METRICS_REDIS_URL", None) or getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0")
    return redis.Redis.from_url(url)


def _safe_int(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def reset_metrics():
    cli = _client()
    pipe = cli.pipeline()
    pipe.delete("metrics:pending", "metrics:ready", "metrics:failed", "metrics:pending_z", "metrics:timing")
    pipe.set("metrics:start", time.time())
    pipe.execute()


def _ensure_start(cli):
    if not cli.exists("metrics:start"):
        cli.set("metrics:start", time.time())


def mark_pending(doc_id: int):
    """
    Increase pending counters and timestamp the doc for stale detection.
    """
    cli = _client()
    _ensure_start(cli)
    now = time.time()
    pipe = cli.pipeline()
    pipe.incr("metrics:pending")
    pipe.zadd("metrics:pending_z", {doc_id: now})
    pipe.execute()


def mark_ready(doc_id: int, duration_seconds: float):
    """
    Move a doc from pending to ready and update timing stats.
    """
    cli = _client()
    _ensure_start(cli)
    pipe = cli.pipeline()
    pipe.decr("metrics:pending")
    pipe.incr("metrics:ready")
    pipe.zrem("metrics:pending_z", doc_id)
    pipe.hincrbyfloat("metrics:timing", "sum", max(duration_seconds, 0))
    pipe.hincrby("metrics:timing", "count", 1)
    pipe.execute()


def mark_failed(doc_id: int):
    cli = _client()
    _ensure_start(cli)
    pipe = cli.pipeline()
    pipe.decr("metrics:pending")
    pipe.incr("metrics:failed")
    pipe.zrem("metrics:pending_z", doc_id)
    pipe.execute()


def get_metrics(timeout_seconds: int = 120) -> Optional[dict]:
    """
    Returns counters and timings from Redis. If Redis is unreachable, returns None.
    """
    try:
        cli = _client()
        now = time.time()
        pending = _safe_int(cli.get("metrics:pending"))
        ready = _safe_int(cli.get("metrics:ready"))
        failed = _safe_int(cli.get("metrics:failed"))
        stale = cli.zcount("metrics:pending_z", 0, now - timeout_seconds)
        start_val = cli.get("metrics:start")
        started_at = float(start_val) if start_val else None
        timing = cli.hgetall("metrics:timing")
        total = float(timing.get(b"sum", 0) or 0)
        count = _safe_int(timing.get(b"count", 0) or 0)
        avg = round(total / count, 2) if count else None
        elapsed = round(now - started_at, 2) if started_at else None
        rate = round(ready / elapsed, 2) if elapsed and elapsed > 0 else None
        return {
            "pending": pending,
            "ready": ready,
            "failed": failed,
            "stale_pending": stale,
            "avg_seconds": avg,
            "total_seconds": round(total, 2),
            "elapsed_seconds": elapsed,
            "docs_per_sec": rate,
        }
    except Exception:
        return None
