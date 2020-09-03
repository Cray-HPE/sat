# Logging in SAT

The ``sat`` command-line utility performs logging to a file and to stderr
according to the configuration in the ``sat.toml`` config file and options
specified on the command line. The logger named ``sat`` is configured by the
``configure_logging`` function in the ``sat.logging`` module. This function is
called early in the ``main`` function of the module ``sat.main``, which is the
entry point to the command-line utility.

In order to ensure that messages logged by your code respect the configured log
levels for stderr and file output, each module that wants to log should get a
logger object using the name of the module as shown below:

    import logging
    
    LOGGER = logging.getLogger(__name__)

Since the module is within the ``sat`` package, it will exist under the
top-level ``sat`` logger in the hierarchy, and any messages logged will be
handled properly by that top-level logger.

To log a message at a given level, just call the appropriate method of the
logger object. For example:

    LOGGER.debug("About to print a warning.")
    LOGGER.warning("This is a warning.")
 