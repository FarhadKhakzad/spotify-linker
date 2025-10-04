import logging

from spotify_linker.logger import configure_logging, get_logger


def test_configure_logging_sets_root_level() -> None:
    root_logger = logging.getLogger()
    original_level = root_logger.level
    original_handlers = list(root_logger.handlers)

    try:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)

        configure_logging(level=logging.DEBUG)

        assert logging.getLogger().level == logging.DEBUG
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        for handler in original_handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(original_level)


def test_get_logger_returns_named_logger() -> None:
    logger = get_logger("spotify_linker.tests")

    assert logger.name == "spotify_linker.tests"
