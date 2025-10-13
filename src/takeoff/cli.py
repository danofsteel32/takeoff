import logging
from pathlib import Path

import click

from . import pdf


def setup_logging(level: int, log_file: Path | None = None):
    root_logger = logging.getLogger()
    # It's good practice to clear existing handlers to avoid duplicates
    # if this function is called multiple times (e.g., in testing).
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 2. Set the overall logging level
    root_logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all messages,

    # 3. Create a console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(levelname)s: %(name)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)  # Set console level based on user input
    root_logger.addHandler(console_handler)

    # 4. Create a file handler if a log file is specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, mode="a")
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)  # File usually logs everything
            root_logger.addHandler(file_handler)
            print(f"Logging to file: {log_file}")
        except IOError as e:
            print(f"Could not open log file {log_file}: {e}")
            # Fallback: Just log to console if file logging fails
            pass


@click.command()
@click.argument("blueprint", type=click.Path(exists=True, path_type=Path))
@click.option("-v", "--verbose", count=True)
@click.option(
    "--log-file", type=click.Path(dir_okay=False, writable=True, path_type=Path)
)
def takeoff(blueprint: Path, verbose: int, log_file: Path | None = None):
    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    setup_logging(level, log_file)
    pages = pdf.process(blueprint)
