import os
import logging
import sys
import logging
from datetime import datetime

def setup_logging(log_directory = "logs"):
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_file = f'{log_directory}/log_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.txt'
    # Configure the root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:%(levelname)s:%(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Add a custom exception hook to log uncaught exceptions
    def exception_handler(exc_type, exc_value, exc_traceback):
        logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.excepthook = exception_handler

def setup_logger():
    """Set up a logger for the calling module based on its name."""
    setup_logging()
    logger = logging.getLogger(__name__)
    return logger
