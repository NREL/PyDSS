"""Contains logging configuration data."""

import logging
import logging.config


def setup_logging(name, filename=None, console_level=logging.INFO,
                  file_level=logging.INFO):
    """Configures logging to file and console.

    Parameters
    ----------
    name : str
        logger name
    filename : str | None
        log filename
    console_level : int, optional
        console log level
    file_level : int, optional
        file log level

    """
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "basic": {
                "format": "%(message)s"
            },
            "short": {
                "format": "%(asctime)s - %(levelname)s [%(name)s "
                          "%(filename)s:%(lineno)d] : %(message)s",
            },
            "detailed": {
                "format": "%(asctime)s - %(levelname)s [%(name)s "
                          "%(filename)s:%(lineno)d] : %(message)s",
            },
        },
        "handlers": {
            "console": {
                "level": console_level,
                "formatter": "short",
                "class": "logging.StreamHandler",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": file_level,
                "filename": filename,
                "mode": "w",
                "formatter": "detailed",
            },
        },
        "loggers": {
            name: {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
        },
    }

    if filename is None:
        log_config["handlers"].pop("file")
        log_config["loggers"][name]["handlers"].remove("file")

    logging.config.dictConfig(log_config)
    logger = logging.getLogger(name)

    return logger
