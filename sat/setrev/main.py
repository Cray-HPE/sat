"""
The main entry point for the setrev subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import datetime
import logging
import os
import sys
from collections import namedtuple

import yaml

from sat.config import get_config_value


LOGGER = logging.getLogger(__name__)


def is_valid_date(date_text):
    """Check validity of date string.

    Args:
        date_text: The string to verify.

    Returns:
        True if date_text is a valid date (wrt this program),
        False otherwise.
    """

    if date_text == '':
        return True

    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def get_site_data(sitefile):
    """Load data from existing sitefile.

    Args:
        sitefile: path to site info file.

    Returns:
        Dictionary of keys and values for what was read.
        Returns empty dict if file did not exist or could not be parsed.

    Raises:
        PermissionError: If the sitefile exists but could not be read.
    """

    s = ''
    data = {}

    try:
        with open(sitefile, 'r') as f:
            s = f.read()
    except FileNotFoundError:
        # it is not an error if this file doesn't already exist.
        return {}
    except PermissionError:
        # but we should not attempt to write to it if we can't read it.
        LOGGER.error('Site file {} has insufficient permissions.'.format(sitefile))
        raise

    try:
        data = yaml.safe_load(s)
    except yaml.parser.ParserError:
        LOGGER.warning('Site file {} is not in yaml format. It will be erased if you continue.'.format(sitefile))
        return {}

    # ensure we parsed the file correctly.
    if type(data) is not dict:
        return {}

    # yaml.safe_load will attempt 'helpful' conversions to different types,
    # and we only want strings.
    for key, value in data.items():
        data[key] = str(value)

    return data


def input_site_data(data):
    """Loop through entries and prompt user for input.

    User will be re-prompted on invalid input.

    Args:
        data (io): dict-ref containing values to input. Will be modified.

    Returns:
        None
    """

    # Use two lists of field names and validators. Validators
    # are functions that accept a single entry and return True or False.
    Entry = namedtuple('Entry', 'name help validate')
    fields = [
        Entry(name='Serial number', help='', validate=lambda x: True),
        Entry(name='Site name', help='', validate=lambda x: True),
        Entry(name='System name', help='', validate=lambda x: True),
        Entry(name='System install date', help='(YYYY-mm-dd, empty for today)', validate=is_valid_date),
        Entry(name='System type', help='', validate=lambda x: True),
    ]

    # input and validate entries. Give the user the option to keep
    # current entries, and loop until valid input is entered.
    for entry in fields:
        isvalid = False

        while not isvalid:
            thisentry = None
            if entry.name in data:
                thisentry = data[entry.name]
                help = '(press enter to keep current value of "{}")'.format(thisentry)
                thisentry = input(' '.join([entry.name, help, ': ']))
                if not thisentry:
                    thisentry = data[entry.name]
            else:
                thisentry = input(' '.join([entry.name, entry.help, ': ']))

            isvalid = entry.validate(thisentry)
            if not isvalid:
                print('"{}" is an invalid entry for "{}".'.format(thisentry, entry.name))
            else:
                data[entry.name] = thisentry

    # if date was not entered, then set it to today
    if not data['System install date']:
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        data['System install date'] = today


def write_site_data(sitefile, data):
    """Write data to sitefile in yaml format.

    It is considered a critical error by setrev if this function fails.

    Args:
        sitefile: Path to sitefile.
        data: Dictionary of data to write.

    Returns:
        None.

    Raises:
        Exception of unknown type if the write to the sitefile failed.
    """

    # write entries to file as yaml - avoid using PyYAML
    with open(sitefile, 'w') as of:
        try:
            of.write('---\n')
        except Exception:
            LOGGER.critical('Writing to {}. Check its integrity!'.format(sitefile))
            raise

        for key, value in data.items():
            try:
                of.write('{}: {}\n'.format(key, value))
            except Exception:
                LOGGER.critical('Writing {}. Check the integrity of {} !'.format(key, sitefile))
                raise


def setrev(args):
    """Populate Shasta's site-specific information.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.
    """

    data = {}

    # determine sitefile location from command line args or config file.
    sitefile = args.sitefile
    if not sitefile:
        sitefile = get_config_value('general.site_info')
        if not sitefile:
            LOGGER.error('No sitefile specified on commandline or in config file.')
            sys.exit(1)

    # ensure our ability to create the file
    dir = os.path.dirname(sitefile)
    if not os.path.exists(dir):
        LOGGER.error('Directory {} does not exist.'.format(dir))
        sys.exit(1)

    data = get_site_data(sitefile)

    # check to see if we can open the file for writing.
    try:
        stream = open(sitefile, 'a')
    except PermissionError:
        LOGGER.error('Cannot open {} for writing.'.format(sitefile))
        sys.exit(1)
    except FileNotFoundError:
        LOGGER.error('Cannot create {}.'.format(sitefile))
        sys.exit(1)

    # when we reopen the file, we want to overwrite it.
    stream.close()

    input_site_data(data)
    write_site_data(sitefile, data)
