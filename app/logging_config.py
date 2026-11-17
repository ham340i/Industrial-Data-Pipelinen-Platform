# AI contribution: 50% or more AI-generated
"""Central logging configuration for the API process.

Every module logs through ``logging.getLogger(__name__)``; this module is the
only place that decides level, format and destination. Messages carry
identifiers (run, node, project, correlation ID) and error codes, never data
values, credentials or machine paths: see docs/security/security-plan.md.
"""

from __future__ import annotations

import logging
import logging.config

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def configure_logging(level: str = "INFO") -> None:
    """Send ``app.*`` records to stderr at ``level``; safe to call repeatedly."""
    chosen = level.upper() if level.upper() in LEVELS else "INFO"
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"standard": {"format": LOG_FORMAT}},
            "handlers": {
                "stderr": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "stream": "ext://sys.stderr",
                }
            },
            "loggers": {
                # Propagation stays on so test and host handlers still see records.
                "app": {"handlers": ["stderr"], "level": chosen, "propagate": True}
            },
        }
    )
