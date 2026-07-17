# =====================================================
# ✅ LOGGING UTILITIES
# =====================================================
import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from core.paths import get_project_root

LOGS_DIR = os.path.join(get_project_root(), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:  # avoid duplicate handlers
        # File handler
        log_file = os.path.join(LOGS_DIR, f"log_{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=7)
        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger
