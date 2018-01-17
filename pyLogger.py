import logging

def getLogger(name, LoggingLevel = logging.DEBUG):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler1 = logging.StreamHandler()
    handler1.setFormatter(formatter)
    handler2 = logging.FileHandler(filename=name + '.log')
    handler2.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(LoggingLevel)
    logger.addHandler(handler1)
    logger.addHandler(handler2)
    return logger
