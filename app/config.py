"""Application configuration.

The compatibility import keeps existing deployments using ``flask_config`` working.
"""

from flask_config import Config

__all__ = ["Config"]