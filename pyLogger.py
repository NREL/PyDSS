import logging

def getLogger(name, LoggerOptions=None):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')



    logger = logging.getLogger(name)
    logger.setLevel(LoggerOptions['Logging Level'])
    if LoggerOptions['Display on screen']:
        handler1 = logging.StreamHandler()
        handler1.setFormatter(formatter)
        logger.addHandler(handler1)
    if LoggerOptions['Log to external file']:
        handler2 = logging.FileHandler(filename=name + '.log')
        handler2.setFormatter(formatter)
        logger.addHandler(handler2)
    return logger
