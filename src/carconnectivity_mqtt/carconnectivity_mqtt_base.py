"""Module containing the commandline interface for the carconnectivity package."""
from __future__ import annotations
from typing import TYPE_CHECKING

from enum import Enum
import logging

from carconnectivity.carconnectivity_base import CLI

from carconnectivity_plugins.mqtt._version import __version__

if TYPE_CHECKING:
    pass

LOG = logging.getLogger("carconnectivity-mqtt")


class Formats(Enum):
    """
    Formats is an enumeration that defines the output formats supported by the application.

    Attributes:
        STRING (str): Represents the string format.
        JSON (str): Represents the JSON format.
    """
    STRING = 'string'
    JSON = 'json'

    def __str__(self) -> str:
        return self.value


def main() -> None:
    """
    Entry point for the car connectivity mqtt application.

    This function initializes and starts the command-line interface (CLI) for the
    car connectivity application using the specified logger and application name.
    """
    cli: CLI = CLI(logger=LOG, name='carconnectivity-mqtt', description='Commandline Interface to interact with Car Services of various brands',
                   subversion=__version__)
    cli.main()
