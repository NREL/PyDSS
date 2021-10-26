import logging
import os
from PyDSS.simulation_input_models import SimulationSettingsModel, LoggingModel


def getLogger(name, path, settings: LoggingModel):
    log_filename = os.path.join(path, name + '.log')

    if settings.clear_old_log_file:
        if os.path.exists(log_filename):
            os.remove(log_filename)

    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    logger = logging.getLogger(name)
    logger.setLevel(settings.logging_level)
    if settings.enable_console:
        handler1 = logging.StreamHandler()
        handler1.setFormatter(formatter)
        logger.addHandler(handler1)
    if settings.enable_file:
        if not os.path.exists(path):
            os.mkdir(path)
        handler2 = logging.FileHandler(filename=log_filename)
        handler2.setFormatter(formatter)
        logger.addHandler(handler2)
    return logger


def getReportLogger(LoggerTag, path, settings: LoggingModel):
    log_filename = os.path.join(path, "{}__reports.log".format(LoggerTag))
    # if os.path.exists(log_filename):
    #     os.remove(log_filename)

    logger = logging.getLogger("Reports")
    logger.handlers = []

    if settings.clear_old_log_file:
        if os.path.exists(log_filename):
            os.remove(log_filename)

    handler = logging.FileHandler(filename=log_filename)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # if settings.enable_console:
    #     handler1 = logging.StreamHandler()
    #     handler1.setFormatter(formatter)
    #     logger.addHandler(handler1)
    return logger


def getLoggerTag(settings: SimulationSettingsModel):
    return settings.project.active_project + "__" + settings.project.active_scenario
