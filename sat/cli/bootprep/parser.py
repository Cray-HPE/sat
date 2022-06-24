#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
The parser for the bootprep subcommand.
"""
from inflect import engine

from sat.cli.bootprep.constants import DEFAULT_PUBLIC_KEY_FILE, DOCS_ARCHIVE_FILE_NAME, EXAMPLE_FILE_NAME

OUTPUT_DIR_OPTION = '--output-dir'

inflector = engine()


def add_skip_and_overwrite_options(parser, short_item, long_item):
    """Add skip and overwrite options for existing objects of the given type.

    Adds two mutually exclusive options of the form:
        --skip-existing-{short_item}s
        --overwrite-{short_item}s

    Args:
        parser (argparse.ArgumentParser): the parser to which options should
            be added
        short_item (str): the short name for the item that will be used in the
            option strings, e.g. 'config'
        long_item (str): the long name for the item that will be used in the
            help information for the options

    Returns:
        None
    """
    group = parser.add_mutually_exclusive_group()
    plural_short_item = inflector.plural(short_item)
    plural_long_item = inflector.plural(long_item)

    group.add_argument(
        f'--skip-existing-{plural_short_item}', action='store_true',
        help=f'Skip creating any {plural_long_item} for which {inflector.a(long_item)} '
             f'with the same name already exists.'
    )
    group.add_argument(
        f'--overwrite-{plural_short_item}', action='store_true',
        help=f'Overwrite any {plural_long_item} for which {inflector.a(long_item)} '
             f'with the same name already exists.'
    )


def add_output_dir_option(parser):
    """Add the --output-dir option.

    Args:
        parser (argparse.ArgumentParser): the parser to which options should
            be added

    Returns:
        None
    """
    parser.add_argument(
        OUTPUT_DIR_OPTION, '-o', default='.',
        help='The directory to which files output by the "--save-files" option '
             'to the run action or by the "generate-docs" or "generate-example" '
             'actions should be output.'
    )


def add_bootprep_subparser(subparsers):
    """Add the bootprep subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    bootprep_parser = subparsers.add_parser(
        'bootprep', help='Prepare to boot nodes with images and configurations.',
        description='Create CFS configurations, build IMS images, customize '
                    'IMS images with CFS configurations, and create BOS session '
                    'templates which can then be used to boot nodes in the '
                    'system.'
    )

    actions_subparsers = bootprep_parser.add_subparsers(
        metavar='action', dest='action', help='The action to execute.'
    )
    _add_bootprep_run_subparser(actions_subparsers)
    _add_bootprep_generate_docs_subparser(actions_subparsers)
    _add_bootprep_view_schema_subparser(actions_subparsers)
    _add_bootprep_example_subparser(actions_subparsers)


def _add_bootprep_generate_docs_subparser(subparsers):
    """Add the options for 'sat bootprep generate-docs'.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    docs_subparser = subparsers.add_parser(
        'generate-docs', help='Generate bootprep schema documentation.',
        description=f'Generate human-readable HTML documentation from the '
                    f'bootprep input file schema and save it to a file named '
                    f'{DOCS_ARCHIVE_FILE_NAME} in the directory specified by '
                    f'{OUTPUT_DIR_OPTION}.'
    )
    add_output_dir_option(docs_subparser)


def _add_bootprep_view_schema_subparser(subparsers):
    """Add the options for 'sat bootprep view-schema'.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    subparsers.add_parser(
        'view-schema', help='View bootprep input file schema.',
        description='View the bootprep input file jsonschema schema in '
                    'raw YAML format.'
    )


def _add_bootprep_example_subparser(subparsers):
    """Add the options for 'sat bootprep generate-example'.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    example_subparser = subparsers.add_parser(
        'generate-example', help='Generate an example bootprep input file.',
        description='Generate an example bootprep input file using product '
                    'catalog data. The output will be saved to a file named '
                    f'{EXAMPLE_FILE_NAME} in the directory specified by '
                    f'{OUTPUT_DIR_OPTION}.'
    )
    add_output_dir_option(example_subparser)


def _add_bootprep_run_subparser(subparsers):
    """Add the options for 'sat bootprep run'

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    run_subparser = subparsers.add_parser(
        'run', help='Run sat bootprep.',
        description='Create images, configurations and session templates.'
    )
    run_subparser.add_argument(
        'input_file',
        help='Path to the input YAML file that defines the configurations, '
             'images, and session templates to create.')
    run_subparser.add_argument(
        '--dry-run', '-d', action='store_true',
        help='Do a dry-run. Do not actually create CFS configurations, '
             'build images, customize images, or create BOS session templates, '
             'but walk through all the other steps.'
    )
    run_subparser.add_argument(
        '--save-files', '-s', action='store_true',
        help='Save files that could be passed to the CFS and BOS to create CFS '
             'configurations and BOS session templates, respectively.'
    )
    run_subparser.add_argument(
        '--no-resolve-branches', action='store_false', dest='resolve_branches',
        help='Do not resolve branch names to corresponding commit hashes before '
             'creating CFS configurations.'
    )

    add_skip_and_overwrite_options(run_subparser, 'config', 'configuration')
    add_skip_and_overwrite_options(run_subparser, 'image', 'image')
    add_skip_and_overwrite_options(run_subparser, 'template', 'session template')
    add_output_dir_option(run_subparser)

    public_key_group = run_subparser.add_mutually_exclusive_group()
    public_key_file_option = '--public-key-file-path'
    public_key_id_option = '--public-key-id'
    default_behavior = (f'If neither {public_key_file_option} nor {public_key_id_option} is specified, '
                        f'the default is to use the public key located at {DEFAULT_PUBLIC_KEY_FILE}.')
    public_key_group.add_argument(
        public_key_file_option,
        help=f'The SSH public key file to use when building images with IMS. '
             f'{default_behavior}'
    )
    public_key_group.add_argument(
        public_key_id_option,
        help=f'The id of the SSH public key stored in IMS to use when building images '
             f'with IMS. {default_behavior}'
    )
