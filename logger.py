import sys
from loguru import logger


def logging_setup():
    logger.remove()

    # Add a handler for DEBUG level messages (blue)
    logger.add(
        sys.stdout,
        colorize=True,
        format="<blue>{time:HH:mm:ss.SS}</blue> | <level>{message}</level>",
        level="DEBUG",
        filter=lambda record: record["level"].name == "DEBUG",
    )

    # Add a handler for INFO level messages (green)
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:HH:mm:ss.SS}</green> | <level>{message}</level>",
        level="INFO",
        filter=lambda record: record["level"].name == "INFO",
    )

    # Add a handler for WARNING level messages (orange)
    logger.add(
        sys.stdout,
        colorize=True,
        format="<yellow>{time:HH:mm:ss.SS}</yellow> | <level>{message}</level>",
        level="WARNING",
        filter=lambda record: record["level"].name == "WARNING",
    )

    # Add a handler for ERROR level messages (red)
    logger.add(
        sys.stdout,
        colorize=True,
        format="<red>{time:HH:mm:ss.SS}</red> | <level>{message}</level>",
        level="ERROR",
        filter=lambda record: record["level"].name == "ERROR",
    )


logging_setup()

# Example usage
# logger.debug("This is a debug message.")
# logger.info("This is an info message.")
# logger.warning("This is a warning message.")
# logger.error("This is an error message.")
