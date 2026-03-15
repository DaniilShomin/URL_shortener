import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pythonjsonlogger.json import JsonFormatter


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_dir = "logs"
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
            file_handler = RotatingFileHandler(
                f"{log_dir}/app.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError):
            pass

    return logger


logger = setup_logging()
