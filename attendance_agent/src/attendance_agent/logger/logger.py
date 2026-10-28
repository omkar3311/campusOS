import logging
import sys

from attendance_agent.config import settings


def setup_logger() -> logging.Logger:
    """Create and configure application logger."""

    logger = logging.getLogger(
        "attendance_agent"
    )

    if logger.handlers:
        return logger

    level = getattr(
        logging,
        settings.LOG_LEVEL.upper(),
        logging.INFO,
    )

    logger.setLevel(level)

    handler = logging.StreamHandler(
        sys.stdout
    )

    formatter = logging.Formatter(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)

    logger.propagate = False

    return logger


logger = setup_logger()