"""
The parser for the bootprep subcommand.

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""
from sat.cli.bootprep.constants import DEFAULT_PUBLIC_KEY_FILE


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

    bootprep_parser.add_argument(
        '--dry-run', '-d', action='store_true',
        help='Do a dry-run. Do not actually create CFS configurations, '
             'build images, customize images, or create BOS session templates, '
             'but walk through all the other steps.'
    )
    bootprep_parser.add_argument(
        '--save-files', '-s', action='store_true',
        help='Save files that could be passed to the CFS and BOS to create CFS '
             'configurations and BOS session templates, respectively.'
    )
    bootprep_parser.add_argument(
        '--output-dir', '-o', default='.',
        help='The directory to which files output by the "--save-files" option '
             'should be output.'
    )

    existing_configs_group = bootprep_parser.add_mutually_exclusive_group()
    existing_configs_group.add_argument(
        '--skip-existing-configs', action='store_true',
        help='Skip creating any configurations that already exist.'
    )
    existing_configs_group.add_argument(
        '--overwrite-configs', action='store_true',
        help='Overwrite any configurations that already exist.'
    )

    public_key_group = bootprep_parser.add_mutually_exclusive_group()
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

    existing_images_group = bootprep_parser.add_mutually_exclusive_group()
    existing_images_group.add_argument(
        '--skip-existing-images', action='store_true',
        help='Skip creating any images for which an image of the same name '
             'already exists.'
    )
    existing_images_group.add_argument(
        '--overwrite-images', action='store_true',
        help='Overwrite (delete and re-create) any images for which an image '
             'of the same name already exists.'
    )

    bootprep_parser.add_argument(
        'input_file', help='Path to the input YAML file that defines the '
                           'configurations, images, and session templates '
                           'to create.')
