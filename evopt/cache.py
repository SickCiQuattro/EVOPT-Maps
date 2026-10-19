import re
import time
from pathlib import Path

CACHE_DIR = Path("cache")


def slug(text):
    return re.sub(r"\W+", "-", text.lower()).strip("-")


def cached(path, ttl_days, build, load, save):
    """Legge `path` se più recente di `ttl_days`, altrimenti ricostruisce e riscrive.

    Un file illeggibile vale come scaduto: è una cache, si rigenera.
    """
    path = Path(path)
    if path.exists() and time.time() - path.stat().st_mtime < ttl_days * 86400:
        try:
            return load(path)
        except Exception:  # noqa: BLE001, S110 - qualunque errore di lettura (json, xml, ...) vuol dire ricostruire
            pass
    value = build()
    path.parent.mkdir(parents=True, exist_ok=True)
    save(value, path)
    return value
