import logging
import os
from logging.handlers import RotatingFileHandler

SERVICE_NAME = os.getenv("SERVICE_NAME", "transactions_service")
LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"{SERVICE_NAME}.log")


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(ch)

    fh = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5)
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(fh)


configure_logging()
logging = __import__("logging")
