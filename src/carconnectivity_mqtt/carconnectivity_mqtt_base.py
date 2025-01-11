"""Module containing the commandline interface for the carconnectivity package."""
from __future__ import annotations
from typing import TYPE_CHECKING

from enum import Enum
import sys
import os
import argparse
import logging
import tempfile
import time
import json

from json_minify import json_minify

from carconnectivity import carconnectivity, errors, util
from carconnectivity._version import __version__ as __carconnectivity_version__

from carconnectivity_plugins.mqtt._version import __version__

if TYPE_CHECKING:
    pass

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
DEFAULT_LOG_LEVEL = "ERROR"

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


def main() -> None:  # noqa: C901 # pylint: disable=too-many-statements,too-many-branches,too-many-locals
    """
    Entry point for the carconnectivity-cli command-line interface.

    This function sets up the argument parser, handles logging configuration, and processes commands
    such as 'list', 'get', 'set', 'save', and 'shell'. It interacts with the CarConnectivity service
    to perform various operations based on the provided arguments.

    Commands:
        - list: Lists available resource IDs and exits.
        - get: Retrieves resources by ID and exits.
        - set: Sets resources by ID and exits.
        - save: Saves resources by ID to a file.
        - shell: Starts the WeConnect shell.

    Arguments:
        --version: Displays the version of the CLI and CarConnectivity.
        config: Path to the configuration file.
        --tokenfile: File to store the token (default: system temp directory).
        -v, --verbose: Increases logging verbosity.
        --logging-format: Specifies the logging format (default: '%(asctime)s:%(levelname)s:%(message)s').
        --logging-date-format: Specifies the logging date format (default: '%Y-%m-%dT%H:%M:%S%z').
        --hide-repeated-log: Hides repeated log messages from the same module.
    """
    parser = argparse.ArgumentParser(
        prog='carconectivity-cli',
        description='Commandline Interface to interact with Car Services of various brands')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__} (using CarConnectivity {__carconnectivity_version__})')
    parser.add_argument('config', help='Path to the configuration file')

    default_temp = os.path.join(tempfile.gettempdir(), 'carconnectivity.token')
    parser.add_argument('--tokenfile', help=f'file to store token (default: {default_temp})', default=default_temp)
    default_cache_temp = os.path.join(tempfile.gettempdir(), 'carconnectivity.cache')
    parser.add_argument('--cachefile', help=f'file to store cache (default: {default_cache_temp})', default=default_cache_temp)
    parser.add_argument('--healthcheckfile', help='file to store healthcheck data', default=None)

    logging_group = parser.add_argument_group('Logging')
    logging_group.add_argument('-v', '--verbose', action="append_const", help='Logging level (verbosity)', const=-1,)
    logging_group.add_argument('--logging-format', dest='logging_format', help='Logging format configured for python logging '
                               '(default: %%(asctime)s:%%(module)s:%%(message)s)', default='%(asctime)s:%(levelname)s:%(message)s')
    logging_group.add_argument('--logging-date-format', dest='logging_date_format', help='Logging format configured for python logging '
                               '(default: %%Y-%%m-%%dT%%H:%%M:%%S%%z)', default='%Y-%m-%dT%H:%M:%S%z')
    logging_group.add_argument('--hide-repeated-log', dest='hide_repeated_log', help='Hide repeated log messages from the same module', action='store_true')

    args = parser.parse_args()
    log_level = LOG_LEVELS.index(DEFAULT_LOG_LEVEL)
    for adjustment in args.verbose or ():
        log_level = min(len(LOG_LEVELS) - 1, max(log_level + adjustment, 0))

    logging.basicConfig(level=LOG_LEVELS[log_level], format=args.logging_format, datefmt=args.logging_date_format)
    if args.hide_repeated_log:
        for handler in logging.root.handlers:
            handler.addFilter(util.DuplicateFilter())

    try:  # pylint: disable=too-many-nested-blocks
        try:
            with open(file=args.config, mode='r', encoding='utf-8') as config_file:
                try:
                    config_dict = json.loads(json_minify(config_file.read(), strip_space=False))
                    car_connectivity = carconnectivity.CarConnectivity(config=config_dict, tokenstore_file=args.tokenfile, cache_file=args.cachefile)
                    car_connectivity.startup()
                    try:
                        while True:
                            if args.healthcheckfile is not None:
                                with open(file=args.healthcheckfile, mode='w', encoding='utf-8') as healthcheck_file:
                                    if car_connectivity.is_healthy():
                                        healthcheck_file.write('healthy')
                                    else:
                                        healthcheck_file.write('unhealthy')
                            time.sleep(60)
                    except KeyboardInterrupt:
                        LOG.info('Keyboard interrupt received, shutting down...')

                        car_connectivity.shutdown()
                except json.JSONDecodeError as e:
                    LOG.critical('Could not load configuration file %s (%s)', args.config, e)
                    sys.exit('Could not load configuration file')
        except FileNotFoundError as e:
            LOG.critical('Could not find configuration file %s (%s)', args.config, e)
            sys.exit('Could not find configuration file')
    except errors.AuthenticationError as e:
        LOG.critical('There was a problem when authenticating with one or multiple services: %s', e)
        sys.exit('There was a problem when authenticating with one or multiple services')
    except errors.APICompatibilityError as e:
        LOG.critical('There was a problem when communicating with one or multiple services.'
                     ' If this problem persists please open a bug report: %s', e)
        sys.exit('There was a problem when communicating with one or multiple services.')
    except errors.RetrievalError as e:
        LOG.critical('There was a problem when communicating with one or multiple services: %s', e)
        sys.exit('There was a problem when communicating with one or multiple services.')
    except errors.ConfigurationError as e:
        LOG.critical('There was a problem with the configuration: %s', e)
        sys.exit('There was a problem with the configuration')
    except KeyboardInterrupt:
        sys.exit("killed")
