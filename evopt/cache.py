import re
import time
from pathlib import Path

CACHE_DIR = Path("cache")


def slug(text):
    return re.sub(r"\W+", "-", text.lower()).strip("-")


def cached(path, ttl_days, build, load, save):
    """Read `path` if newer than `ttl_days`, otherwise rebuild and rewrite it.

    An unreadable file counts as expired: it is a cache, it can be regenerated.
    """
    path = Path(path)
    if path.exists() and time.time() - path.stat().st_mtime < ttl_days * 86400:
        try:
            return load(path)
        except Exception:  # noqa: BLE001, S110 - any read error (json, xml, ...) means rebuild
            pass
    value = build()
    path.parent.mkdir(parents=True, exist_ok=True)
    save(value, path)
    return value
