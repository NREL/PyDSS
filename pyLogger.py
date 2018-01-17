import logging

def getLogger(name, LoggingLevel = logging.DEBUG):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(LoggingLevel)
    logger.addHandler(handler)
    return logger
