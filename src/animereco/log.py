import logging


def setup_logging(name: str):
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    debug_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(debug_format)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler("logs/animereco.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(debug_format)
    logger.addHandler(file_handler)

    return logger
