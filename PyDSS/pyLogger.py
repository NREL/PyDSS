import logging
import os

LOGGER_DEFAULTS = {
    'Logging Level': logging.INFO,
    'Log to external file': True,
    'Display on screen': True,
    'Clear old log files': False,
}


def getLogger(name, path, LoggerOptions=None):
    if LoggerOptions['Clear old log files']:
        test = os.listdir(os.getcwd())
        for item in test:
            if item.endswith(".log"):
                os.remove(item)
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    logger = logging.getLogger(name)
    logger.setLevel(LoggerOptions['Logging Level'])
    if LoggerOptions['Display on screen']:
        handler1 = logging.StreamHandler()
        handler1.setFormatter(formatter)
        logger.addHandler(handler1)
    if LoggerOptions['Log to external file']:
        if not os.path.exists(path):
            os.mkdir(path)
        handler2 = logging.FileHandler(filename=os.path.join(path, name + '.log'))
        handler2.setFormatter(formatter)
        logger.addHandler(handler2)
    return logger
