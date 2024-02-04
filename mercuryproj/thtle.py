import atexit

import json
import logging
import logging.config
import logging.handlers
import pathlib
from queue import Queue

logger = logging.getLogger(__name__)


def setup_logging():
    log_queue = Queue()
    queue_handler = logging.handlers.QueueHandler(log_queue)
    config_file = pathlib.Path("logging_configs/configs.json")

    with open(config_file) as f_in:
        config = json.load(f_in)

    logging.config.dictConfig(config)
    logger.addHandler(queue_handler)

    queue_listener = logging.handlers.QueueListener(log_queue, *logger.handlers)

    queue_listener.start()
    atexit.register(queue_listener.stop)


setup_logging()
logging.basicConfig(level="INFO")
logging.debug("debug message")
logging.warning("debug message")


def main():
    setup_logging()
    logging.basicConfig(level="INFO")
    logging.debug("debug message")
    logging.warning("debug message")


if __name__ == "__main__":
    main()
