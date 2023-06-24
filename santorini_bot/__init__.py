import logging


# formatter = logging.Formatter(
#     fmt="[%(asctime)s GMT] %(levelname)-8s: [%(name)s] %(message)s",
#     datefmt="%Y-%m-%d %H:%M:%S",
# )
# formatter.converter = time.gmtime

stream_handler = logging.StreamHandler()

logger = logging.getLogger(__name__)
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

GAME_LOG_DELIMITER = "|"
