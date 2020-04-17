"""
Module for obtaining product version information.

Copyright 2020 Cray Inc. All Rights Reserved.
"""
from collections import OrderedDict
import logging
import os

from sat.constants import MISSING_VALUE

LOGGER = logging.getLogger(__name__)

# This is the only required key in a file to consider it a file that contains
# version information about an installed product.
REQUIRED_KEY = 'PRODUCT'

# The name of the column that contains the name of the product release file
RELEASE_FILE_COLUMN = 'RELEASE_FILE'


def _get_unique_keys(ordered_dicts):
    """Gets a list of unique keys from the list of OrderedDicts.

    Args:
        ordered_dicts (list): A list of OrderedDicts

    Returns:
        A list of the unique keys maintaining the order of the keys as seen
        when iterating over the list of OrderedDicts.
    """
    seen_keys = set()
    unique_keys = []
    for ordered_dict in ordered_dicts:
        for key in ordered_dict:
            if key not in seen_keys:
                seen_keys.add(key)
                unique_keys.append(key)
    return unique_keys


def get_product_versions(release_dir_path='/opt/cray/etc/release'):
    """Gets the product versions from files in `release_dir_path`.

    Args:
        The path to the release directory containing product version files.

    Returns:
        A tuple of (headings, data_rows) where headings is a list of strings
        representing the headings for the data, and data_rows is a list of
        lists where each element is a list representing one row of data.

        The headings will be the union of headings seen across every product
        file, and they will be returned in the same order as seen when iterating
        over the product files in alphabetical order by file name.

        Every element of data_rows will have a value for each heading, but the
        value may be `MISSING_VALUE` for headings which are not present in that
        particular product file.
    """
    product_dicts = []

    try:
        listed_dir = sorted(os.listdir(release_dir_path))
    except OSError as err:
        LOGGER.error("Unable to read product versions from '%s': %s",
                     release_dir_path, err)
        return [], []

    for path in listed_dir:
        full_path = os.path.join(release_dir_path, path)
        if not os.path.isfile(full_path):
            LOGGER.info("Skipping '%s' because it is not a file.", full_path)
            continue

        try:
            with open(full_path, 'r') as f:
                # read().splitlines() removes trailing '\n' unlike readlines()
                product_lines = f.read().splitlines()
        except OSError as err:
            LOGGER.warning("Skipping unreadable file '%s': %s",
                           release_dir_path, err)
            continue

        product_dict = OrderedDict()
        product_dict[RELEASE_FILE_COLUMN] = path

        for line in product_lines:
            try:
                key, value = line.split('=', maxsplit=1)
            except ValueError:
                LOGGER.info("Skipping line without '=' in '%s': %s",
                            full_path, line)
                continue

            # Remove any double quotes used in the values
            product_dict[key] = value.strip('"')

        if REQUIRED_KEY in product_dict:
            product_dicts.append(product_dict)

    headings = _get_unique_keys(product_dicts)
    data_rows = [[product_dict.get(key, MISSING_VALUE) for key in headings]
                 for product_dict in product_dicts]

    return headings, data_rows
