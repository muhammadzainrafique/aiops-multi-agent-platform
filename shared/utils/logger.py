# shared/utils/logger.py
"""
Shared structured logger used by all three agents.
Usage: from shared.utils.logger import get_logger
"""
import logging
import os


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance.
    Log level is controlled via LOG_LEVEL environment variable.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
