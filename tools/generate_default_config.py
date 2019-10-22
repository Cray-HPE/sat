#!/usr/bin/env python3

"""Creates a default configuration from the supplied config.py file in
TOML format.

To use:
1. First install the dependencies of this project:
     `pip install -r requirements.txt`
2. Run this script with the file `config.py` from this project as its
   argument. The file can be any file with a variable named
   `SAT_CONFIG_SPEC` in it.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import argparse
from importlib.machinery import SourceFileLoader
import sys
from textwrap import dedent, indent

import toml


def extract_config_spec(path, spec_var_name):
    """Gets the configuration spec from a given file.

    The given source file will be imported under the name
    'config_module'.

    Args:
        path (str): a path to the Python source file containing the
            configuration spec.

    Returns: a dict representing a default configuration according
        to the given spec.

    """
    try:
        loader = SourceFileLoader('config_module', path)
        module = loader.load_module()
        spec = getattr(module, spec_var_name)
        return {
            section: {
                option: '' if callable(spec.default) else spec.default
                for option, spec in options.items()
            }
            for section, options in spec.items()
        }

    except IOError as ioerr:
        print("ERROR: {}".format(ioerr))

    except SyntaxError as synerr:
        print("ERROR: Couldn't parse source file: {}"
              .format(synerr))

    except AttributeError as attrerr:
        print("ERROR: Problem finding or parsing variable {} in file {}: {}"
              .format(spec_var_name, path, attrerr))

    raise SystemExit(1)


def process_toml_output(toml_str):
    """Comments out non-header lines, and adds a Cray copyright statement to a string.

    Args:
        toml_str (str): some arbitrary TOML content.

    Returns:
        a string containing the same TOML content, with options commented
        out and a copyright statement prepended.

    """
    copyright_stmt = """\
    Default configuration file for SAT.
    Copyright 2019 Cray Inc. All Rights Reserved.

    """
    return indent(dedent(copyright_stmt) + toml_str, "# ",
                  predicate=lambda line: line != '\n' and not line.startswith('['))


def create_parser():
    """Creates the ArgumentParser object used by this script.

    Returns: an ArgumentParser object.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('config_spec_file', help='path to a Python source file '
                        'containing a variable from which '
                        'to generate the default configuration.')
    parser.add_argument('-o', '--output', help='path to which the default '
                        'config should be written.')
    parser.add_argument('--spec-var-name', default='SAT_CONFIG_SPEC',
                        help='variable name of the config spec from the '
                        'given Python source file.')

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    config_spec = extract_config_spec(args.config_spec_file, args.spec_var_name)

    try:
        output_stream = open(args.output, 'w') if args.output else sys.stdout
        with output_stream:
            toml_str = toml.dumps(config_spec)
            output_stream.write(process_toml_output(toml_str))

    except IOError as ioerr:
        print("ERROR: {}".format(ioerr))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
