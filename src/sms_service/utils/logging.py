import logging
import os
import sys


def setup_logging():
    log_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | [%(threadName)s] | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    os.makedirs("logs", exist_ok=True)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    file_handler = logging.FileHandler("logs/service.log", encoding="utf-8")
    file_handler.setFormatter(log_formatter)

    logging.basicConfig(
        level=logging.DEBUG if os.getenv("LOGLEVEL", "debug") == "debug" else logging.INFO,
        handlers=[console_handler, file_handler],
    )
