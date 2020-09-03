# Configuration in SAT

The ``sat`` command-line utility reads its configuration from a TOML-formatted
config file. The TOML format was chosen for consistency with the ``cray`` CLI
and for ease of machine parsing. As described in the ``sat`` man page, the
``sat`` CLI looks at ``/etc/sat.toml`` for its configuration by default. This
can be overridden with an alternate path in the environment variable
``SAT_CONFIG_FILE``.

The config file contains sections and option-value pairs in those sections. This
is represented as a dictionary whose keys are the section names and whose values
are dictionaries mapping from option names to values within those sections. The
sections can be used to separate the options by the type of functionality they
control.

The ``sat.config`` module defines the specification of each possible config
option, including its type, default value, validation function (if any), and
the command-line option that can override it (if any). It also defines a global
module variable, ``CONFIG``, that is used to store the loaded ``SATConfig``
object. Subcommands can use the ``get_config_value`` function to get the value
for a given configuration option. This function will load the config from the
appropriate file if it has not yet been loaded, log warnings for any invalid
config values and set them to their defaults, and obtain the value for the given
option accounting for any command-line overrides as appropriate.

## Defining a New Config Option

To define a new config file option, a new entry must be added to the dictionary
``SAT_CONFIG_SPEC`` in ``sat.config``. The ``SAT_CONFIG_SPEC`` is a dictionary
whose keys are the section names of the config file and whose values are
dictionaries mapping from option names to ``OptionSpec`` objects.

The ``OptionSpec`` is a ``namedtuple`` class whose named attributes are:

* ``type``: the type of the option. E.g., ``bool``, ``str``, ``int``. In the
  TOML config file, these options must have values of this type in order for the
  option to validate. That means ``str`` values must be quoted, ``int`` values
  must not be quoted, and ``bool`` values must be ``true`` or ``false``.
* ``default``: the default value for the option. This must be of the correct
  type. This value will be used if the option is not specified in the config
  file or if an invalid value is given for the option.
* ``validation_func``: the validation function. This function should take the
  option value as its argument and should validate that the value is acceptable.
  If the option value is invalid, it should raise a ``ConfigValidationError``.
  If no validation should be performed, this can be set to ``None`` for the
  ``OptionSpec``.
* ``cmdline_arg``: The name of a command-line argument that should override
  the value of this config file option. If the value of the command-line
  argument with this name is not ``None``, then the command-line argument value
  will be used instead of the config file option. As a result, if you wish to
  set up a config file option that can be overridden, be sure that the argument
  has the value ``None`` when it is not specified by the user.

### Example of Defining a New Config Option

The following example shows how to add a string config file option named
``color`` that defaults to the string ``'nocolor'``, is validated by a function
named ``validate_color``, and can be overridden by a command-line argument named
``color``.

    SAT_CONFIG_SPEC = {
    ...
        'format': {
            'color': OptionSpec(string, 'nocolor', validate_color, 'color'),
        },
    ...
    }
    
    def validate_color(color):
        """Validates the given action.
    
        Args:
            color (str): The color string to validate.
    
        Returns:
            None
    
        Raises:
            ConfigValidationError: If the given `color` is not valid.
        """
        valid_colors = ('nocolor', 'red', 'blue', 'green')
        if action not in valid_colors:
            raise ConfigValidationError(
                "Color '{}' is not one of the valid colors: {}".format(
                    color, ", ".join(valid_colors)
                )
            )

## Getting a Config Option Value

To get a config option value, use ``get_config_value``. For example:

    from sat.config import get_config_value
    LOGGER.debug('The format color is %s.', get_config_value('format.color'))

## Generating a Config File

The RPM spec file for the ``cray-sat`` rpm includes a step to generate the
default config file that is installed at ``/etc/sat.toml``. This uses the script
``tools/generate_default_config.py``. This script can be used in a Python
virtual environment to generate a config file from the ``SAT_CONFIG_SPEC`` in
``sat.config`` at any time. The script's usage information can be viewed with
the ``--help`` or ``-h`` option.

Here is an example of running this script to generate the config file::

    (sat) user@local-mbp sat $ ./tools/generate_default_config.py -o ~/tmp/sat.toml ./sat/config.py
    (sat) user@local-mbp sat $ cat ~/tmp/sat.toml
    # Default configuration file for SAT.
    # (C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.
    ...
    [api_gateway]
    # host = "api-gw-service-nmn.local"
    # cert_verify = true
    # username = ""
    # token_file = ""
    ...

The config file generated by the script contains all sections defined in the
``SAT_CONFIG_SPEC`` in  ``sat.config``, and it contains all options and their
default values commented out.
