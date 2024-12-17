import coloredlogs, logging

bot_logger: logging.Logger = logging.getLogger("bot")

def init():
    logging.basicConfig(level=logging.INFO)
    coloredlogs.install(level=logging.INFO)

def info(logger: logging.Logger, msg: str):
    logger.info(msg)

def error(logger: logging.Logger, msg: str):
    logger.error(msg)

def debug(logger: logging.Logger, msg: str):
    logger.debug(msg)

def bot_info(msg: str):
    bot_logger.info(msg)

def bot_error(msg: str):
    bot_logger.error(msg)

def bot_debug(msg: str):
    bot_logger.debug(msg)
