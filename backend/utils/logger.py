"""
logger.py - Structured logging for Legal Lens.

Outputs to both console and file for debugging and audit purposes.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path


def setup_logger(
    name: str = "legal_lens",
    log_dir: str = "logs",
    log_level: int = logging.INFO,
) -> logging.Logger:
    """
    Set up a structured logger with console and file handlers.
    
    Args:
        name: Logger name.
        log_dir: Directory to store log files.
        log_level: Logging level (default INFO).
    
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Log format
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (daily rotation)
    log_file = log_path / f"legal_lens_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Default logger instance
logger = setup_logger()


if __name__ == "__main__":
    logger.info("Logger test: INFO message")
    logger.warning("Logger test: WARNING message")
    logger.error("Logger test: ERROR message")
