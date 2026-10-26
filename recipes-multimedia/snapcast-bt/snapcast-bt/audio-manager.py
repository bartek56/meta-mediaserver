#!/usr/bin/python3

"""Start the MediaServer event-driven audio manager."""

from __future__ import annotations

import logging
import os

from audio_manager.app import AudioManagerApplication


def configure_logging() -> None:
    """Configure Python logging from ``AUDIO_MANAGER_LOG_LEVEL``."""

    raw_level = os.environ.get("AUDIO_MANAGER_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, raw_level, logging.INFO)
    if raw_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        logging.getLogger("audio-manager").warning(
            "Unknown AUDIO_MANAGER_LOG_LEVEL=%r; using INFO",
            raw_level,
        )
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d: %(message)s",
        datefmt="%Y-%m-%dT %H:%M:%S",
    )


def main() -> int:
    """Create the application and return its process exit status."""

    configure_logging()
    application = AudioManagerApplication()
    return application.run()


if __name__ == "__main__":
    raise SystemExit(main())
